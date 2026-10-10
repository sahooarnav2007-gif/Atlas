import time
import traceback
from typing import Dict, Any, Callable, Type
from pydantic import BaseModel, ValidationError
from atlas.evidence.ledger import ToolExecutionEnvelope

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Type[BaseModel]] = {}
        self._docstrings: Dict[str, str] = {}

    def register(self, name: str, input_schema: Type[BaseModel]):
        def decorator(func: Callable):
            self._tools[name] = func
            self._schemas[name] = input_schema
            self._docstrings[name] = func.__doc__ or ""
            return func
        return decorator

    def execute(self, tool_name: str, arguments: Dict[str, Any], dataset_id: str, dataset_version: str = "v1") -> ToolExecutionEnvelope:
        if tool_name not in self._tools:
            return ToolExecutionEnvelope(
                tool_name=tool_name,
                status="error",
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                validated_parameters=arguments,
                error_message=f"Unknown tool '{tool_name}'",
                warnings=[f"Tool {tool_name} is not registered in catalogue."]
            )

        start_time = time.time()
        schema_cls = self._schemas[tool_name]
        try:
            validated = schema_cls(**arguments)
            validated_dict = validated.model_dump()
        except ValidationError as ve:
            return ToolExecutionEnvelope(
                tool_name=tool_name,
                status="error",
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                validated_parameters=arguments,
                error_message=f"Parameter validation error: {str(ve)}",
                warnings=["Invalid arguments provided to analytical tool."]
            )

        try:
            handler = self._tools[tool_name]
            result_data, warnings = handler(dataset_id=dataset_id, **validated_dict)
            duration_ms = int((time.time() - start_time) * 1000)

            return ToolExecutionEnvelope(
                tool_name=tool_name,
                status="success",
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                validated_parameters=validated_dict,
                result=result_data,
                warnings=warnings,
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolExecutionEnvelope(
                tool_name=tool_name,
                status="error",
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                validated_parameters=validated_dict,
                error_message=str(e),
                warnings=[f"Execution failed: {str(e)}"],
                duration_ms=duration_ms
            )

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "name": name,
                "description": self._docstrings.get(name, ""),
                "parameters_schema": self._schemas[name].model_json_schema()
            }
            for name in self._tools
        }

registry = ToolRegistry()
