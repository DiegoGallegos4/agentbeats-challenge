from datetime import date as date_module
import os
from typing import Any, Iterable
from pathlib import Path
import pandas as pd
from pydantic import BaseModel, ValidationError
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart, DataPart
from a2a.utils import get_message_text, new_agent_text_message

from messenger import Messenger
from agentbeats.portfolio import portfolio_manager
from agentbeats.portfolio.tools import data_manager as portfolio_data_manager
from agentbeats.portfolio.tools.sp500_utils import get_sp500_tickers


class EvalRequest(BaseModel):
    """Request format sent by the AgentBeats platform to agents."""
    participants: dict[str, str] # role -> agent URL
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
        config = request.config or {}
        if "tasks" not in config:
            participant_roles = {role for role, url in request.participants.items() if url}
            missing_roles = set(self.required_roles) - participant_roles
            if missing_roles:
                return False, f"Missing roles: {missing_roles}"

            missing_config_keys = set(self.required_config_keys) - set(config.keys())
            if missing_config_keys:
                return False, f"Missing config keys: {missing_config_keys}"

        # Add additional request validation here

        return True, "ok"

    def _find_market_file(self, ticker: str) -> Path | None:
        base_dir = Path(portfolio_data_manager.BASE_DIR)
        candidates = list(base_dir.glob(f"*/market/{ticker}.csv"))
        if not candidates:
            return None
        candidates.sort(key=lambda path: path.parent.parent.name, reverse=True)
        return candidates[0]

    def _load_history(self, ticker: str) -> pd.DataFrame:
        csv_path = self._find_market_file(ticker)
        if not csv_path or not csv_path.exists():
            return pd.DataFrame()
        df = pd.read_csv(csv_path)
        if df.empty or "date" not in df.columns:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        return df

    def _find_index(self, df: pd.DataFrame, target_date: str) -> int | None:
        if df.empty or "date" not in df.columns:
            return None
        target_ts = pd.to_datetime(target_date, errors="coerce")
        if pd.isna(target_ts):
            return None
        matches = df.index[df["date"] == target_ts]
        if matches.empty:
            return None
        return int(matches[0])

    def _predict_for_task(self, task: dict[str, Any]) -> Any:
        level = int(task.get("level", 0))
        end_time = task.get("end_time")
        target_date = str(pd.to_datetime(end_time, errors="coerce").date()) if end_time else None
        if not target_date:
            return None

        if level == 2:
            tickers = task.get("tickers") or self.default_tickers
            predictions = []
            for symbol in tickers:
                df = self._load_history(symbol)
                idx = self._find_index(df, target_date)
                if idx is None or idx < 2:
                    continue
                prev_close = float(df.loc[idx - 1, "close"])
                prior_close = float(df.loc[idx - 2, "close"])
                if prev_close > prior_close:
                    predictions.append(str(symbol).upper())
            return predictions

        ticker = task.get("ticker")
        if not ticker:
            return None
        df = self._load_history(str(ticker))
        idx = self._find_index(df, target_date)
        if idx is None or idx < 2:
            return None

        prev_close = float(df.loc[idx - 1, "close"])
        prior_close = float(df.loc[idx - 2, "close"])
        if level == 1:
            return "Yes" if prev_close > prior_close else "No"
        if level == 3:
            return round(prev_close, 2)
        if level == 4:
            prev_high = float(df.loc[idx - 1, "high"])
            prev_low = float(df.loc[idx - 1, "low"])
            return round(prev_high - prev_low, 2)
        return None

    def _filter_missing_market_data(self, tickers: list[str], target_date: str) -> list[str]:
        base_dir = Path(portfolio_data_manager.BASE_DIR)
        missing = []
        for ticker in tickers:
            market_path = base_dir / target_date / "market" / f"{ticker}.csv"
            if not market_path.exists():
                missing.append(ticker)
        return missing

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
        data_root = config.get("data_root")
        if data_root:
            resolved_root = str(Path(data_root).expanduser().resolve())
            portfolio_data_manager.BASE_DIR = resolved_root
            os.environ["AGENTBEATS_DATA_DIR"] = resolved_root
        tasks = config.get("tasks")
        if tasks:
            await updater.update_status(
                TaskState.working, new_agent_text_message("Generating FinanceX predictions...")
            )
            predictions = []
            for task in tasks:
                predictions.append(
                    {
                        "id": task.get("id"),
                        "prediction": self._predict_for_task(task),
                    }
                )

            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text="FinanceX predictions generated.")),
                    Part(root=DataPart(data={"predictions": predictions})),
                ],
                name="Result",
            )
            return

        target_date = config.get("date") or date_module.today().isoformat()
        tickers = self._resolve_tickers(config.get("tickers"))
        download = bool(config.get("download", False))

        await updater.update_status(
            TaskState.working, new_agent_text_message("Running portfolio analysis...")
        )

        if download:
            missing = self._filter_missing_market_data(tickers, target_date)
            if missing:
                portfolio_data_manager.download_all_data(missing, target_date)
            else:
                print(f"Data already present for {len(tickers)} tickers on {target_date}, skipping download.")

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
