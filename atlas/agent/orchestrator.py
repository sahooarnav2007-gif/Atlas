import time
import json
import uuid
from typing import Dict, Any, List, Optional
from atlas.config import settings
from atlas.tools.registry import registry
from atlas.evidence.ledger import EvidenceLedger, ToolExecutionEnvelope
from atlas.memory.service import memory_service
from atlas.persistence.db import SessionFactory, DatasetRecord, AnalysisRecord
from atlas.agent.adapter import LLMAdapter

class AgentState:
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentOrchestrator:
    def __init__(self):
        self.adapter = LLMAdapter()
        self.ledger = EvidenceLedger()

    def run_analysis(
        self,
        dataset_id: str,
        question: str,
        options: Optional[Dict[str, Any]] = None,
        analysis_id: Optional[str] = None
    ) -> Dict[str, Any]:
        options = options or {}
        analysis_id = analysis_id or f"an_{uuid.uuid4().hex[:8]}"
        state = AgentState.PENDING
        warnings: List[str] = []
        start_time = time.time()

        db = SessionFactory()
        try:
            # 1. Resolve dataset and schema
            dataset = db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id).first()
            if not dataset:
                return {
                    "analysis_id": analysis_id,
                    "status": "failed",
                    "error": f"Dataset {dataset_id} not found."
                }

            schema = json.loads(dataset.schema_info)
            dataset_version = dataset.version
            dataset_family = dataset.dataset_family

            # 2. Retrieve relevant persistent memory
            columns = list(schema.get("columns", {}).keys())
            memories = memory_service.retrieve_memories(
                dataset_family=dataset_family,
                columns=columns,
                db_session=db
            )

            # 3. Build structured analysis plan
            state = AgentState.PLANNING
            available_tools = list(registry.list_tools().keys())
            raw_plan = self.adapter.plan_steps(
                question=question,
                schema=schema,
                memories=memories,
                available_tools=available_tools
            )

            # 4. Validate plan against execution budget
            max_steps = min(len(raw_plan), settings.max_agent_steps)
            plan = raw_plan[:max_steps]
            if len(raw_plan) > settings.max_agent_steps:
                warnings.append(f"Plan exceeded max agent steps limit of {settings.max_agent_steps}; truncated.")

            # Record analysis record in DB
            rec = AnalysisRecord(
                analysis_id=analysis_id,
                dataset_id=dataset_id,
                question=question,
                status="running",
                plan=json.dumps(plan)
            )
            db.merge(rec)
            db.commit()

            # 5. Execute plan steps with retry limit and bounded execution
            state = AgentState.EXECUTING
            execution_envelopes: List[ToolExecutionEnvelope] = []
            visualization_figures = []

            for step_idx, step in enumerate(plan):
                tool_name = step.get("tool_name")
                arguments = step.get("arguments", {})

                # Retry loop
                envelope = None
                for attempt in range(settings.max_tool_retries + 1):
                    envelope = registry.execute(
                        tool_name=tool_name,
                        arguments=arguments,
                        dataset_id=dataset_id,
                        dataset_version=dataset_version
                    )
                    if envelope.status == "success":
                        break
                    elif attempt < settings.max_tool_retries:
                        warnings.append(f"Retrying tool '{tool_name}' (attempt {attempt + 2})")

                execution_envelopes.append(envelope)
                self.ledger.record_execution(
                    envelope,
                    assumptions=[step.get("description", "")]
                )

                if envelope.status == "success" and tool_name == "generate_visualization":
                    fig_spec = envelope.result.get("plotly_figure")
                    if fig_spec:
                        visualization_figures.append(fig_spec)

            # 6. Compose answer from verified evidence
            state = AgentState.SYNTHESIZING
            raw_results = [env.model_dump() for env in execution_envelopes]
            answer_text = self.adapter.synthesize_answer(
                question=question,
                plan=plan,
                results=raw_results,
                memories_applied=memories
            )

            state = AgentState.COMPLETED
            duration_total = int((time.time() - start_time) * 1000)

            result_payload = {
                "analysis_id": analysis_id,
                "dataset_id": dataset_id,
                "dataset_version": dataset_version,
                "status": "completed",
                "question": question,
                "answer": answer_text,
                "plan": plan,
                "memories_applied": memories,
                "execution_trace": raw_results,
                "visualizations": visualization_figures,
                "warnings": warnings,
                "duration_ms": duration_total
            }

            # Update DB
            rec = db.query(AnalysisRecord).filter(AnalysisRecord.analysis_id == analysis_id).first()
            if rec:
                rec.status = "completed"
                rec.evidence_backed_response = answer_text
                rec.tool_trace = json.dumps(raw_results)
                rec.warnings = json.dumps(warnings)
                db.commit()

            return result_payload

        except Exception as e:
            db.rollback()
            return {
                "analysis_id": analysis_id,
                "dataset_id": dataset_id,
                "status": "failed",
                "error": str(e),
                "warnings": warnings
            }
        finally:
            db.close()

orchestrator = AgentOrchestrator()
