"""Shell completion generation for Agent Pulse.

Generates completion scripts for bash, zsh, and fish shells.
Usage:
    agent-pulse completions bash >> ~/.bashrc
    agent-pulse completions zsh >> ~/.zshrc
    agent-pulse completions fish > ~/.config/fish/completions/agent-pulse.fish
"""

import click


BASH_COMPLETION = """# Bash completion for agent-pulse
_agent_pulse_completion() {
    local IFS=$'\n'
    local words

    _init_completion || return

    # Subcommands
    local subcommands="alerts budget compare config doctor export export-html health history models optimize plugins report search session snapshot status top web init timeline notify scan completions"

    # Global options
    local global_opts="--version --json --hours --limit --db --dev-root --source --model --watch --interval --theme --no-banner --help"

    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=($(compgen -W "$subcommands $global_opts" -- "${COMP_WORDS[1]}"))
        return
    fi

    local cmd="${COMP_WORDS[1]}"
    case "$cmd" in
        theme|--theme)
            COMPREPLY=($(compgen -W "default dracula monokai light nord catppuccin solarized-light" -- "${COMP_WORDS[COMP_CWORD]}"))
            ;;
        top|-s|--sort)
            COMPREPLY=($(compgen -W "tokens cost tools duration messages" -- "${COMP_WORDS[COMP_CWORD]}"))
            ;;
        export|-f|--format)
            COMPREPLY=($(compgen -W "json csv" -- "${COMP_WORDS[COMP_CWORD]}"))
            ;;
        completions)
            COMPREPLY=($(compgen -W "bash zsh fish" -- "${COMP_WORDS[COMP_CWORD]}"))
            ;;
        notify)
            COMPREPLY=($(compgen -W "setup status test" -- "${COMP_WORDS[COMP_CWORD]}"))
            ;;
        *)
            COMPREPLY=($(compgen -W "$global_opts" -- "${COMP_WORDS[COMP_CWORD]}"))
            ;;
    esac
}

complete -F _agent_pulse_completion agent-pulse
"""

ZSH_COMPLETION = """#compdef agent-pulse

_agent_pulse() {
    local -a commands
    commands=(
        'alerts:Check for cost/token threshold alerts'
        'budget:Budget tracker with daily/monthly limits'
        'compare:Compare activity between two time periods'
        'config:Manage configuration'
        'doctor:Run diagnostic checks'
        'export:Export session data to JSON or CSV'
        'export-html:Export a self-contained HTML report'
        'health:CI-friendly health check with exit codes'
        'history:Activity trends over time'
        'models:Detailed model analytics'
        'optimize:Analyze usage and suggest cheaper alternatives'
        'plugins:List registered data source plugins'
        'report:Generate a daily/weekly summary report'
        'search:Search sessions by keyword'
        'session:Show detailed session info'
        'snapshot:Save and compare dashboard snapshots'
        'status:Quick one-line status summary'
        'top:Top sessions ranked by metric'
        'web:Launch web dashboard'
        'init:Interactive setup wizard'
        'timeline:Session activity timeline'
        'notify:Webhook notification management'
        'scan:Auto-discover AI agent sources'
        'completions:Generate shell completion scripts'
    )

    _arguments -C \
        '(--version)'--version'[Show version]' \
        '(--json)'--json'[Output as JSON]' \
        '(--hours)'--hours'[Hours of history]' \
        '(--limit)'--limit'[Max sessions]' \
        '(--db)'--db'[Hermes database path]' \
        '(--dev-root)'--dev-root'[Projects directory]' \
        '(--source)'--source'[Filter by source]' \
        '(--model)'--model'[Filter by model]' \
        '(-w --watch)'{-w,--watch}'[Watch mode]' \
        '(--interval)'--interval'[Refresh interval]' \
        '(--theme)'--theme'[Color theme]:theme:(default dracula monokai light nord catppuccin solarized-light)' \
        '(--no-banner)'--no-banner'[Skip banner]' \
        '(-h --help)'{-h,--help}'[Show help]' \
        '*:: :->subcmds' && return 0

    if (( CURRENT == 1 )); then
        _describe -t commands 'agent-pulse command' commands
        return
    fi

    local -a opts
    case $words[1] in
        top)
            opts=(--sort --limit --hours --db --dev-root --source --model --json)
            _arguments $opts
            ;;
        export)
            opts=(--format --output --hours --limit --db --source --model)
            _arguments $opts
            ;;
        notify)
            _arguments '*::subcmd:(setup status test)'
            ;;
        completions)
            _arguments '*::shell:(bash zsh fish)'
            ;;
    esac
}

_agent_pulse "$@"
"""

FISH_COMPLETION = """# Fish completion for agent-pulse

# Subcommands
set -l commands alerts budget compare config doctor export export-html \
    health history models optimize plugins report search session snapshot \
    status top web init timeline notify scan completions

# Disable file completions by default
complete -c agent-pulse -f

# Global options
complete -c agent-pulse -l version -d 'Show version'
complete -c agent-pulse -l json -d 'Output as JSON'
complete -c agent-pulse -l hours -d 'Hours of history' -r
complete -c agent-pulse -l limit -d 'Max sessions' -r
complete -c agent-pulse -l db -d 'Hermes database path' -r
complete -c agent-pulse -l dev-root -d 'Projects directory' -r
complete -c agent-pulse -l source -d 'Filter by source' -r
complete -c agent-pulse -l model -d 'Filter by model' -r
complete -c agent-pulse -s w -l watch -d 'Watch mode'
complete -c agent-pulse -l interval -d 'Refresh interval' -r
complete -c agent-pulse -l theme -d 'Color theme' -xa 'default dracula monokai light nord catppuccin solarized-light'
complete -c agent-pulse -l no-banner -d 'Skip banner'
complete -c agent-pulse -s h -l help -d 'Show help'

# Subcommands
complete -c agent-pulse -n __fish_use_subcommand -a alerts -d 'Check alerts'
complete -c agent-pulse -n __fish_use_subcommand -a budget -d 'Budget tracker'
complete -c agent-pulse -n __fish_use_subcommand -a compare -d 'Compare periods'
complete -c agent-pulse -n __fish_use_subcommand -a config -d 'Manage config'
complete -c agent-pulse -n __fish_use_subcommand -a doctor -d 'Run diagnostics'
complete -c agent-pulse -n __fish_use_subcommand -a export -d 'Export data'
complete -c agent-pulse -n __fish_use_subcommand -a export-html -d 'HTML report'
complete -c agent-pulse -n __fish_use_subcommand -a health -d 'Health check'
complete -c agent-pulse -n __fish_use_subcommand -a history -d 'Activity trends'
complete -c agent-pulse -n __fish_use_subcommand -a models -d 'Model analytics'
complete -c agent-pulse -n __fish_use_subcommand -a optimize -d 'Cost optimization'
complete -c agent-pulse -n __fish_use_subcommand -a plugins -d 'List plugins'
complete -c agent-pulse -n __fish_use_subcommand -a report -d 'Summary report'
complete -c agent-pulse -n __fish_use_subcommand -a search -d 'Search sessions'
complete -c agent-pulse -n __fish_use_subcommand -a session -d 'Session detail'
complete -c agent-pulse -n __fish_use_subcommand -a snapshot -d 'Dashboard snapshots'
complete -c agent-pulse -n __fish_use_subcommand -a status -d 'Quick status'
complete -c agent-pulse -n __fish_use_subcommand -a top -d 'Top sessions'
complete -c agent-pulse -n __fish_use_subcommand -a web -d 'Web dashboard'
complete -c agent-pulse -n __fish_use_subcommand -a init -d 'Setup wizard'
complete -c agent-pulse -n __fish_use_subcommand -a timeline -d 'Activity timeline'
complete -c agent-pulse -n __fish_use_subcommand -a notify -d 'Notifications'
complete -c agent-pulse -n __fish_use_subcommand -a scan -d 'Discover sources'
complete -c agent-pulse -n __fish_use_subcommand -a completions -d 'Shell completions'

# Top sort options
complete -c agent-pulse -n '__fish_seen_subcommand_from top' -s s -l sort -xa 'tokens cost tools duration messages'

# Export format
complete -c agent-pulse -n '__fish_seen_subcommand_from export' -s f -l format -xa 'json csv'

# Completions shell
complete -c agent-pulse -n '__fish_seen_subcommand_from completions' -xa 'bash zsh fish'

# Notify subcommands
complete -c agent-pulse -n '__fish_seen_subcommand_from notify' -xa 'setup status test'
"""


SHELL_COMPLETIONS = {
    "bash": ("~/.bashrc", "agent-pulse.bash", BASH_COMPLETION),
    "zsh": ("~/.zshrc", "_agent-pulse", ZSH_COMPLETION),
    "fish": ("~/.config/fish/completions/agent-pulse.fish", "agent-pulse.fish", FISH_COMPLETION),
}


def get_completion_script(shell: str) -> str:
    """Get the completion script for a shell.

    Args:
        shell: Shell name (bash, zsh, fish).

    Returns:
        Completion script content.

    Raises:
        ValueError: If shell is not supported.
    """
    if shell not in SHELL_COMPLETIONS:
        raise ValueError(f"Unsupported shell: {shell}. Supported: {', '.join(SHELL_COMPLETIONS)}")
    return SHELL_COMPLETIONS[shell][2]


def get_install_instructions(shell: str) -> str:
    """Get installation instructions for a shell.

    Args:
        shell: Shell name (bash, zsh, fish).

    Returns:
        Human-readable installation instructions.
    """
    if shell not in SHELL_COMPLETIONS:
        return f"Unsupported shell: {shell}"

    rc_file, filename, _ = SHELL_COMPLETIONS[shell]

    if shell == "bash":
        return f"""To install bash completions:

  # Option 1: Add to ~/.bashrc
  eval "$(agent-pulse completions bash)"

  # Option 2: System-wide
  agent-pulse completions bash | sudo tee /etc/bash_completion.d/agent-pulse
"""
    elif shell == "zsh":
        return f"""To install zsh completions:

  # Option 1: Add to ~/.zshrc
  eval "$(agent-pulse completions zsh)"

  # Option 2: Completions directory
  agent-pulse completions zsh > {filename}
  fpath=({filename} $fpath)
  autoload -Uz compinit && compinit
"""
    elif shell == "fish":
        return f"""To install fish completions:

  agent-pulse completions fish > ~/.config/fish/completions/agent-pulse.fish
  # Then restart fish or run: source ~/.config/fish/completions/agent-pulse.fish
"""
    return ""
