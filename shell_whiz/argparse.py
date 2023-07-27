import argparse


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description="Shell Whiz: AI assistant right in your terminal"
    )

    subparsers = parser.add_subparsers(dest="sw_command", required=True)

    subparsers.add_parser("config", help="Configure Shell Whiz")

    ask_parser = subparsers.add_parser("ask", help="Ask Shell Whiz a question")
    ask_parser.add_argument(
        "prompt", nargs="+", type=str, help="Question to ask Shell Whiz"
    )

    explain_parser = subparsers.add_parser(
        "explain", help="Explain a shell command"
    )
    explain_parser.add_argument(
        "command", nargs="+", type=str, help="Shell command to explain"
    )

    return parser
