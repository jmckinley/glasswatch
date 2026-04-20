#!/usr/bin/env python3
"""
Backup CLI for Glasswatch

Commands:
- backup create [--type full|incremental] [--no-encrypt] [--no-s3]
- backup list
- backup restore <id> [--target-db NAME]
- backup verify <id>
- backup prune
- backup status
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from tabulate import tabulate

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.backup_service import BackupService, BackupType


@click.group()
def cli():
    """Glasswatch Backup Management CLI"""
    pass


@cli.command()
@click.option("--type", "backup_type", type=click.Choice(["full", "incremental"]), default="full", help="Backup type")
@click.option("--no-encrypt", is_flag=True, help="Disable encryption")
@click.option("--no-s3", is_flag=True, help="Skip S3 upload")
def create(backup_type: str, no_encrypt: bool, no_s3: bool):
    """Create a new backup"""
    async def _create():
        service = BackupService()
        
        click.echo(f"Creating {backup_type} backup...")
        
        try:
            metadata = await service.create_backup(
                backup_type=BackupType(backup_type),
                encrypt=not no_encrypt,
                upload_s3=not no_s3,
            )
            
            click.echo(f"✅ Backup created successfully!")
            click.echo(f"   ID: {metadata.id}")
            click.echo(f"   Size: {metadata.size_bytes / 1024 / 1024:.2f} MB")
            click.echo(f"   Duration: {metadata.duration_seconds:.2f}s")
            click.echo(f"   Encrypted: {metadata.encryption_enabled}")
            click.echo(f"   S3: {metadata.s3_uploaded}")
            
        except Exception as e:
            click.echo(f"❌ Backup failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_create())


@cli.command()
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list(output_format: str):
    """List all backups"""
    async def _list():
        service = BackupService()
        backups = await service.list_backups()
        
        if not backups:
            click.echo("No backups found.")
            return
        
        if output_format == "json":
            import json
            click.echo(json.dumps([b.to_dict() for b in backups], indent=2))
        else:
            # Sort by date (newest first)
            backups.sort(key=lambda b: b.created_at, reverse=True)
            
            # Format as table
            headers = ["ID", "Type", "Status", "Created", "Size (MB)", "Encrypted", "S3", "Category"]
            rows = []
            
            for backup in backups:
                size_mb = backup.size_bytes / 1024 / 1024 if backup.size_bytes else 0
                rows.append([
                    backup.id,
                    backup.type.value,
                    backup.status.value,
                    backup.created_at.strftime("%Y-%m-%d %H:%M"),
                    f"{size_mb:.2f}",
                    "✓" if backup.encryption_enabled else "✗",
                    "✓" if backup.s3_uploaded else "✗",
                    backup.retention_category,
                ])
            
            click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
            click.echo(f"\nTotal backups: {len(backups)}")
    
    asyncio.run(_list())


@cli.command()
@click.argument("backup_id")
@click.option("--target-db", help="Target database name (defaults to current DB)")
@click.confirmation_option(prompt="⚠️  This will overwrite the target database. Continue?")
def restore(backup_id: str, target_db: Optional[str]):
    """Restore from backup"""
    async def _restore():
        service = BackupService()
        
        click.echo(f"Restoring backup {backup_id}...")
        
        try:
            await service.restore_backup(backup_id, target_db)
            click.echo(f"✅ Backup restored successfully!")
            
        except Exception as e:
            click.echo(f"❌ Restore failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_restore())


@cli.command()
@click.argument("backup_id")
def verify(backup_id: str):
    """Verify backup integrity"""
    async def _verify():
        service = BackupService()
        
        click.echo(f"Verifying backup {backup_id}...")
        
        try:
            is_valid = await service.verify_backup(backup_id)
            
            if is_valid:
                click.echo(f"✅ Backup is valid")
            else:
                click.echo(f"❌ Backup is corrupted or missing", err=True)
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"❌ Verification failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_verify())


@cli.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def prune(yes: bool):
    """Remove expired backups"""
    async def _prune():
        service = BackupService()
        
        if not yes:
            if not click.confirm("This will delete old backups according to retention policy. Continue?"):
                click.echo("Cancelled.")
                sys.exit(0)
        
        click.echo("Pruning old backups...")
        
        try:
            deleted_count = await service.prune_backups()
            click.echo(f"✅ Deleted {deleted_count} old backup(s)")
            
        except Exception as e:
            click.echo(f"❌ Prune failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_prune())


@cli.command()
def status():
    """Show backup system health"""
    async def _status():
        service = BackupService()
        
        try:
            status = await service.get_backup_status()
            
            if status["healthy"]:
                click.echo("✅ Backup system is healthy\n")
            else:
                click.echo("⚠️  Backup system needs attention\n")
            
            click.echo(f"Last backup: {status['last_backup'] or 'Never'}")
            if status["last_backup"]:
                click.echo(f"Hours since last: {status['hours_since_last']}")
            
            click.echo(f"Total backups: {status['total_backups']}")
            click.echo(f"Total size: {status['total_size_mb']} MB")
            
            if status["total_backups"] > 0:
                click.echo(f"\nBy category:")
                click.echo(f"  Daily: {status['by_category']['daily']}")
                click.echo(f"  Weekly: {status['by_category']['weekly']}")
                click.echo(f"  Monthly: {status['by_category']['monthly']}")
            
            click.echo(f"\n{status['message']}")
            
            if not status["healthy"]:
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"❌ Status check failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_status())


if __name__ == "__main__":
    cli()
