"""Main CLI entry point."""

import click
from rich.console import Console
from ..utils.logger import setup_logger
from ..utils.exceptions import LogAnalyzerError


console = Console()


@click.command()
@click.argument('query', required=False)
@click.argument('log_file', required=False)
@click.option('--output-format', '-f', default='human',
              type=click.Choice(['json', 'human']),
              help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config-dir', default='config', help='Configuration directory path')
@click.option('--app-log-file', help='Log file for application logs')
@click.option('--test-config', is_flag=True, help='Test configuration files and exit')
def main(query, log_file, output_format, verbose, config_dir, app_log_file, test_config):
    """AI-powered log analysis using natural language queries."""
    
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    logger = setup_logger(level=log_level, log_file=app_log_file)
    
    # Handle config test mode
    if test_config:
        try:
            from ..utils.config import ConfigManager
            
            config = ConfigManager(config_dir)
            console.print("[green]Testing configuration...[/green]")
            
            # Test entity mappings
            aliases = config.get_entity_aliases('cm')
            console.print(f"CM aliases: {aliases}")
            
            # Test log schema
            columns = config.get_log_columns()
            console.print(f"Default columns: {columns}")
            
            # Test prompts
            prompt = config.get_prompt_template('find')
            console.print(f"Find prompt length: {len(prompt)} characters")
            
            console.print("[green]✓ Configuration test passed[/green]")
            return
            
        except Exception as e:
            console.print(f"[red]Configuration test failed: {e}[/red]")
            exit(1)
    
    # Validate required arguments for analysis
    if not query or not log_file:
        console.print("[red]Error: Both QUERY and LOG_FILE are required for analysis[/red]")
        console.print("Usage: python -m src.cli.main \"your question\" path/to/logfile.csv")
        console.print("Or use --test-config to test configuration")
        exit(1)
    
    # Main analysis functionality
    try:
        console.print(f"[green]Processing: '{query}' in {log_file}[/green]")
        console.print("[blue]LLM will automatically determine the best approach based on your question[/blue]")
        # TODO: Implement unified analysis functionality
        console.print("[yellow]Analysis engine not yet implemented[/yellow]")
        
    except LogAnalyzerError as e:
        console.print(f"[red]Error: {e}[/red]")
        exit(1)


if __name__ == '__main__':
    main()
