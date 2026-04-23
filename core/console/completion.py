from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .command import Command


class CompletionGenerator:
    def __init__(self, commands: dict[str, type["Command"]], binary: str = "aiocraft") -> None:
        self._commands = commands
        self._binary = binary

    def generate(self, shell: str) -> str:
        generators = {
            "bash": self._bash,
            "zsh": self._zsh,
            "fish": self._fish,
            "powershell": self._powershell,
        }
        gen = generators.get(shell)
        if not gen:
            supported = ", ".join(generators)
            raise ValueError(f"Unsupported shell: {shell}. Supported: {supported}")
        return gen()

    def _bash(self) -> str:
        cmds = " ".join(sorted(self._commands))
        b = self._binary
        return (
            f"# Bash completion for {b}\n"
            f"_{b}_completions() {{\n"
            f'    local cur="${{COMP_WORDS[COMP_CWORD]}}"\n'
            f'    local commands="{cmds}"\n'
            f"    if [ $COMP_CWORD -eq 1 ]; then\n"
            f'        COMPREPLY=($(compgen -W "$commands" -- "$cur"))\n'
            f"    fi\n"
            f"}}\n"
            f"complete -F _{b}_completions {b}\n"
        )

    def _zsh(self) -> str:
        b = self._binary
        lines = [f"#compdef {b}", "", f"_{b}() {{", "  local commands=("]
        for name in sorted(self._commands):
            desc = getattr(
                self._commands[name],
                "description",
                "",
            ).replace("'", "\\'")
            lines.append(f"    '{name}:{desc}'")
        lines += [
            "  )",
            '  _describe "command" commands',
            "}",
            f"compdef _{b} {b}",
        ]
        return "\n".join(lines)

    def _fish(self) -> str:
        b = self._binary
        lines = [f"# Fish completion for {b}"]
        for name in sorted(self._commands):
            desc = (
                getattr(
                    self._commands[name],
                    "description",
                    "",
                )
                or name
            )
            lines.append(f"complete -c {b} -n '__fish_use_subcommand' -a '{name}' -d '{desc}'")
        return "\n".join(lines)

    def _powershell(self) -> str:
        b = self._binary
        arr = ", ".join(f"'{n}'" for n in sorted(self._commands))
        return (
            f"# PowerShell completion for {b}\n"
            f"Register-ArgumentCompleter -CommandName {b} -ScriptBlock {{\n"
            f"    param($wordToComplete, $commandAst, $cursorPosition)\n"
            f"    $commands = @({arr})\n"
            f'    $commands | Where-Object {{ $_ -like "$wordToComplete*" }}'
            f" | ForEach-Object {{\n"
            f"        [System.Management.Automation.CompletionResult]"
            f"::new($_, $_, 'ParameterValue', $_)\n"
            f"    }}\n"
            f"}}\n"
        )
