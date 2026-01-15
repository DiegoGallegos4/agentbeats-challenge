from datetime import date as date_module
from typing import Any, Iterable
from pydantic import BaseModel, HttpUrl, ValidationError
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart, DataPart
from a2a.utils import get_message_text, new_agent_text_message

from messenger import Messenger
from agentbeats.portfolio import portfolio_manager
from agentbeats.portfolio.tools import data_manager as portfolio_data_manager
from agentbeats.portfolio.tools.sp500_utils import get_sp500_tickers


class EvalRequest(BaseModel):
    """Request format sent by the AgentBeats platform to agents."""
    participants: dict[str, HttpUrl] # role -> agent URL
    config: dict[str, Any]


class Agent:
    # Fill in: list of required participant roles, e.g. ["pro_debater", "con_debater"]
    required_roles: list[str] = []
    # Fill in: list of required config keys, e.g. ["topic", "num_rounds"]
    required_config_keys: list[str] = []

    def __init__(self):
        self.messenger = Messenger()
        # Initialize other state here
        self.default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    def _resolve_tickers(self, raw: Any) -> list[str]:
        if raw is None or raw == "subset":
            return list(self.default_tickers)
        if raw == "all":
            return get_sp500_tickers()
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(",") if t.strip()]
        if isinstance(raw, Iterable):
            return [str(t).strip() for t in raw if str(t).strip()]
        return list(self.default_tickers)

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        missing_roles = set(self.required_roles) - set(request.participants.keys())
        if missing_roles:
            return False, f"Missing roles: {missing_roles}"

        missing_config_keys = set(self.required_config_keys) - set(request.config.keys())
        if missing_config_keys:
            return False, f"Missing config keys: {missing_config_keys}"

        # Add additional request validation here

        return True, "ok"

    async def run(self, message: Message, updater: TaskUpdater) -> None:
        """Implement your agent logic here.

        Args:
            message: The incoming message
            updater: Report progress (update_status) and results (add_artifact)

        Use self.messenger.talk_to_agent(message, url) to call other agents.
        """
        input_text = get_message_text(message)

        try:
            request: EvalRequest = EvalRequest.model_validate_json(input_text)
            ok, msg = self.validate_request(request)
            if not ok:
                await updater.reject(new_agent_text_message(msg))
                return
        except ValidationError as e:
            await updater.reject(new_agent_text_message(f"Invalid request: {e}"))
            return

        config = request.config or {}
        target_date = config.get("date") or date_module.today().isoformat()
        tickers = self._resolve_tickers(config.get("tickers"))
        download = bool(config.get("download", False))

        await updater.update_status(
            TaskState.working, new_agent_text_message("Running portfolio analysis...")
        )

        if download:
            portfolio_data_manager.download_all_data(tickers, target_date)

        portfolio = portfolio_manager.build_portfolio(tickers, date=target_date)
        if portfolio.empty:
            await updater.reject(new_agent_text_message("No portfolio results generated."))
            return

        weights = portfolio.to_dict(orient="records")
        await updater.add_artifact(
            parts=[
                Part(root=TextPart(text="Portfolio weights generated.")),
                Part(root=DataPart(data={
                    "date": target_date,
                    "tickers": tickers,
                    "weights": weights,
                })),
            ],
            name="Result",
        )
