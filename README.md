<p align="center">
  <img src="https://img.shields.io/pypi/v/shell-whiz" alt="PyPI" />
  <img src="https://img.shields.io/pypi/dm/shell-whiz" alt="PyPI - Downloads" />
  <img
    src="https://img.shields.io/github/stars/beyimjan/shell-whiz"
    alt="GitHub stars"
  />
</p>

Shell Whiz is an AI assistant for the command line. It will help you find the right command to solve your task. This way, you can _save your time and effort_ without diving into documentation, man pages, or searching the web.

<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/assets/109351730/6c716b44-5ea8-4f3d-a08f-9ebae06ae4dc"
  />
</p>

## Installation 🛠️

To install Shell Whiz, run the following command:

```bash
pip install shell-whiz
```

This will add the `sw` command to your `PATH`.

To use the assistant you'll need an API key from OpenAI. Obtain this key by visiting https://platform.openai.com/api-keys. Once you have the key, you can set it either by running `sw config` or by setting the `OPENAI_API_KEY` environment variable.

## Getting started ✨

You can run the assistant directly using `sw ask`, but I recommend creating an alias for it. For example, you can add the following line to the bottom of your `~/.bashrc` file:

```bash
alias '??'='sw ask'
```

PowerShell users can create a function in their [PowerShell profile](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles).

```powershell
function ?? {
  sw ask `
    -s (Get-Command powershell.exe).Source `
    -m gpt-4-turbo-preview `
    -p "I use PowerShell on a daily basis" `
    @Args
}
```

You can also create a function that allows you to save executed commands in history. Here are the functions for Bash and Zsh:

```bash
# ~/.bashrc
whiz-shell() {
  TMPFILE=$(mktemp)
  trap 'rm -f $TMPFILE' EXIT
  if sw ask -o "$TMPFILE" "$@"; then
    if [ -e "$TMPFILE" ]; then
      SW_CMD=$(cat "$TMPFILE")
      history -s $(history 1 | cut -d' ' -f4-)
      history -s "$SW_CMD"
      eval "$SW_CMD"
    else
      echo "Sorry, something went wrong." >&2
    fi
  else
    return 1
  fi
}

alias '??'='whiz-shell'
```

```zsh
# ~/.zshrc
whiz-shell() {
  TMPFILE=$(mktemp)
  trap 'rm -f $TMPFILE' EXIT
  if sw ask -o "$TMPFILE" "$@"; then
    if [ -e "$TMPFILE" ]; then
      SW_CMD=$(cat "$TMPFILE")
      print -s "$SW_CMD"
      eval "$SW_CMD"
    else
      echo "Sorry, something went wrong." >&2
    fi
  else
    return 1
  fi
}

alias '??'='whiz-shell'
```

To track API usage and costs, periodically visit the [OpenAI API Usage](https://platform.openai.com/usage) page.

## Advanced usage 🚀

The assistant can be easily configured for any task using command line arguments.

The most powerful option is `-p "..."` or `--preferences "..."`. This setting can be used to select the shell environment or even the language of the assistant's responses. The default value is `I use Bash on Linux`.

Run `sw ask --help` for more information.

<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/assets/109351730/5753885e-360c-410a-a2fd-b51a014c94c0"
  />
</p>
<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/assets/109351730/be058866-a28d-49ad-9e6e-41d8072ab738"
  />
</p>
