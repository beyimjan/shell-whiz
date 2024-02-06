<p align="center">
  <img src="https://img.shields.io/pypi/v/shell-whiz" alt="PyPI" />
  <img src="https://img.shields.io/pypi/dm/shell-whiz" alt="PyPI - Downloads" />
  <img
    src="https://img.shields.io/github/stars/beyimjan/shell-whiz"
    alt="GitHub stars"
  />
</p>

Shell Whiz is an AI assistant for the command line. It will help you find the right command for your task.

<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/blob/main/examples/files_modified_in_the_last_7_days-20231026.gif?raw=true"
  />
</p>

## All features

- **Command suggestions:** It suggests shell commands based on your input. For example, if you want to know the timestamp of a file, `?? what is the timestamp of file.txt` will suggest `stat -c %y file.txt`, which will print the last modification time of the file.
- **Command explanations:** It will try to explain, piece by piece, what the suggested command will do, so you can learn new things about your shell and the commands you use.
- **Revisions:** If the suggested command is not quite what you want, you can ask for a revision. Another way to use this feature is to start with a simple query and iteratively create a complex command by defining the details.
- **Customization:** You can tweak the behavior of Shell Whiz using command line arguments. For example, you can set PowerShell as your shell, disable automatic explanations, or use any [Chat Completions](https://platform.openai.com/docs/api-reference/chat) model instead of the default `gpt-3.5-turbo-0125` model.

## Installation and setup

To install Shell Whiz, run the following command:

```bash
pip install shell-whiz
```

This will add the `sw` command to your `PATH`.

To use Shell Whiz, you need an API key from OpenAI. Obtain this key by visiting https://platform.openai.com/account/api-keys. Once you have the key, configure Shell Whiz by running the following command:

```bash
sw config
```

### Free API plan for new users

New users receive $5 for free to try and test the API during the first 3 months. However, **it is recommended to upgrade to a paid plan in order to have a more comfortable experience using Shell Whiz**. This is because the free plan has restrictions on the number of requests allowed per minute.

## Upgrading

To upgrade Shell Whiz, run the following command:

```bash
pip install --upgrade shell-whiz
```

## Usage

You can run Shell Whiz directly using `sw ask`, but I recommend creating an alias for it. For example, you can add the following line to the bottom of your `~/.bashrc` file:

```bash
alias ??='sw ask'
```

You can also create a function instead of an alias. This will allow you to save executed commands in history. Here are the functions for Bash and Zsh:

```bash
# ~/.bashrc
whiz-shell () {
  TMPFILE=$(mktemp)
  trap 'rm -f $TMPFILE' EXIT
  if sw ask -o "$TMPFILE" "$@"; then
    if [ -e "$TMPFILE" ]; then
      SW_CMD=$(cat "$TMPFILE")
      history -s $(history 1 | cut -d' ' -f4-)
      history -s "$SW_CMD"
      eval "$SW_CMD"
    else
      echo "Sorry, something went wrong."
    fi
  else
    return 1
  fi
}

alias '??'='whiz-shell'
```

```zsh
# ~/.zshrc
whiz-shell () {
  TMPFILE=$(mktemp)
  trap 'rm -f $TMPFILE' EXIT
  if sw ask -o "$TMPFILE" "$@"; then
    if [ -e "$TMPFILE" ]; then
      SW_CMD=$(cat "$TMPFILE")
      print -s "$SW_CMD"
      eval "$SW_CMD"
    else
      echo "Sorry, something went wrong."
    fi
  else
    return 1
  fi
}

alias '??'='whiz-shell'
```

PowerShell users can create a function in their [PowerShell profile](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles).

```powershell
function ?? {
  # Don't forget to set path to your PowerShell executable
  # GPT-4 is used because other models don't work well with PowerShell
  sw ask --dont-warn `
    -s <powershell executable path> `
    -m gpt-4 `
    -p "I use PowerShell" `
    @Args
}
```

To track API usage and costs, periodically visit the [OpenAI API Usage](https://platform.openai.com/account/usage) page.

## Tips

- To pass an argument beginning with a hyphen, use the `--` delimiter. This separates the command and its arguments. For example, `sw ask -- emulate ARM kernel on versatilepb architecture -cpu cortex-a8`.
- Specify a shell executable using `-s` or `--shell`.
- To select the `gpt-4` model, include `-m gpt-4` or `--model gpt-4`.
- To use the GPT-4 model for explanations, append `--explain-using gpt-4`.
- To disable automatic explanations, include `-n` or `--dont-explain`. Manual explanations can still be requested via the menu.
- Use `--dont-warn` to turn off automatic warnings.
- Set specific preferences by adding `-p "..."` or `--preferences "..."`. This setting is versatile, useful for choosing a shell environment or other preferences, including the language for assistant responses. The default is `I use Bash on Linux`.
- Add `-q` or `--quiet` to hide the menu and finish right away.

I prefer using `alias ??='sw ask --dont-warn -n --'`, but when I encounter a command that I don't fully understand, I choose to explain it using GPT-4 manually.

You should choose the settings that work best for you.

Highly recommend using [IntelliShell](https://github.com/lasantosr/intelli-shell) (a bookmark store for commands) along with Shell Whiz.

<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/raw/main/examples/set_environment_variable-20230924.png"
  />
</p>
<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/raw/main/examples/closed_issues_in_beimzhan_shell_whiz-20230924.png"
  />
</p>

## More examples

<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/raw/main/examples/list_open_ports-20230924.png"
  />
</p>
<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/raw/main/examples/create_a_4_GB_file_with_random_data-20230924.png"
  />
</p>
<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/raw/main/examples/list_processes_sorted_by_memory_usage-20230924.png"
  />
</p>
<p align="center">
  <img
    src="https://github.com/beyimjan/shell-whiz/raw/main/examples/most_frequently_modified_files_in_the_repository-20230924.png"
  />
</p>

## License

Shell Whiz is licensed under the GNU General Public License v3.0.
