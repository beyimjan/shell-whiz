<p align="center">
  <img src="https://github.com/beimzhan/shell-whiz/raw/main/images/shell-whiz.png" />
</p>

<p align="center">
  <img src="https://img.shields.io/pypi/v/shell-whiz" alt="PyPI" />
  <img src="https://img.shields.io/pypi/dm/shell-whiz" alt="PyPI - Downloads" />
  <img
    src="https://img.shields.io/github/stars/beimzhan/shell-whiz"
    alt="GitHub stars"
  />
  <img
    src="https://img.shields.io/github/commit-activity/m/beimzhan/shell-whiz"
    alt="GitHub commit activity"
  />
  <img
    src="https://img.shields.io/github/license/beimzhan/shell-whiz"
    alt="GitHub license"
  />
</p>

Shell Whiz is an AI assistant for the command line. It will help you find the right command for your task.

## All features

- **Command suggestions:** It suggests shell commands based on your input. For example, if you want to know the timestamp of a file, you can run `?? what is the timestamp of file.txt` and it will suggest `stat -c %y file.txt`.
- **Command explanations:** It will try to explain, piece by piece, what the suggested command will do, so you can learn new things about your shell and the commands you use.
- **Revisions:** If the suggested command is not exactly what you need, you are on a different platform, or you want to see other options, you can ask for a revision. It will suggest a different command that is similar to the previous one.

## Supported platforms

Shell Whiz is designed to work on various platforms and shells, but it is best suited for Bash on Linux. However, it may sometimes suggest commands that are not compatible with your specific platform or terminal. If this happens, feel free to request a revision.

## Installation and setup

To install Shell Whiz, run the following command:

```bash
pip install shell-whiz
```

This will add the `sw` command to your PATH.

To use Shell Whiz, you need an API key from OpenAI. You can obtain this key by visiting https://platform.openai.com/account/api-keys. Once you have the key, you can configure Shell Whiz by running the following command:

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

<p align="center">
  <img
    src="https://github.com/beimzhan/shell-whiz/blob/main/examples/files_modified_in_the_last_7_days-20230915.gif?raw=true"
  />
</p>

You can run Shell Whiz directly using `sw ask`, but I recommend creating an alias for it. For example, you can add the following line to your `~/.bashrc` file:

```bash
alias ??='sw ask'
```

To track API usage and costs, you can check the [OpenAI API Usage](https://platform.openai.com/account/usage) page.

## Tips

- If you want to pass an argument that starts with a hyphen, you can use `--` to separate the command from the arguments. For example, `sw ask -- emulate ARM kernel on versatilepb architecture -cpu cortex-a8`.
- Add `-m gpt-4` or `--model gpt-4` to use the `gpt-4` model instead of the standard `gpt-3.5-turbo` model. However, this will cost more and may take longer.
- Add `--explain-using-gpt-4` to use the `gpt-4` model for the explanatory part.
- Use `-n` or `--dont-explain` to disable automatic explanations. You can still request an explanation through the menu when a command is suggested.

## More examples

<p align="center">
  <img
    src="https://github.com/beimzhan/shell-whiz/blob/main/examples/create_a_4_GB_file_with_random_data-20230915.gif?raw=true"
  />
</p>
<p align="center">
  <img
    src="https://github.com/beimzhan/shell-whiz/blob/main/examples/list_processes_sorted_by_memory_usage-20230915.gif?raw=true"
  />
</p>
<p align="center">
  <img
    src="https://github.com/beimzhan/shell-whiz/blob/main/examples/most_frequently_modified_files_in_the_repository-20230915.gif?raw=true"
  />
</p>

## License

Shell Whiz is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for more information.
