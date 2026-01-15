import argparse

from .pnl_tracker import calculate_pnl


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate portfolio PnL.")
    parser.add_argument("--date", type=str, required=True, help="Weights date (YYYY-MM-DD)")
    parser.add_argument("--pnl_date", type=str, required=True, help="PnL calculation date (YYYY-MM-DD)")
    args = parser.parse_args()

    calculate_pnl(args.date, args.pnl_date)


if __name__ == "__main__":
    main()
