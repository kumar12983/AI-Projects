# -*- coding: utf-8 -*-
"""
Engagement Analysis Automation - End-to-End Orchestrator
---------------------------------------------------------
Automates the complete workflow:
1. Download input files from SharePoint (WIPs, Bills, BoB)
2. Prepare Bills and BoB files (extract IDs, calculate billings)
3. Run engagement analysis
4. Upload results to SharePoint
5. Send notification to team

Usage:
    python run_engagement_analysis.py --config workflow_config.json

For scheduled execution (Windows Task Scheduler):
    schtasks /create /tn "EngagementAnalysis" /tr "python run_engagement_analysis.py" /sc weekly /d MON /st 06:00
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Import existing modules
from sharepoint_integration import SharePointClient
from prepare_bills import prepare_bills_export
from prepare_bob import prepare_bob_export
from fy_engagement_analysis import run as run_analysis


class EngagementAnalysisWorkflow:
    """Orchestrates the complete engagement analysis workflow."""
    
    def __init__(self, config_file: str):
        """Initialize workflow with configuration."""
        self.config = self._load_config(config_file)
        self.work_dir = Path(self.config.get('work_directory', './work'))
        self.work_dir.mkdir(exist_ok=True)
        self.sp_client = None
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def _load_config(self, config_file: str) -> dict:
        """Load workflow configuration."""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def setup_sharepoint(self) -> None:
        """Initialize SharePoint client and authenticate."""
        print("\n" + "="*60)
        print("STEP 1: Authenticating with SharePoint")
        print("="*60)
        
        sp_config_file = self.config.get('sharepoint_config', 'sharepoint_config.json')
        self.sp_client = SharePointClient(sp_config_file)
        
        auth_type = self.config.get('auth_type', 'delegated')
        if auth_type == 'app':
            self.sp_client.authenticate_app_only()
        else:
            self.sp_client.authenticate_delegated()
    
    def download_inputs(self) -> Dict[str, str]:
        """Download input files from SharePoint."""
        print("\n" + "="*60)
        print("STEP 2: Downloading input files from SharePoint")
        print("="*60)
        
        downloads = self.config['downloads']
        site_name = downloads['site_name']
        folder = downloads['folder_path']
        library = downloads.get('library_name', 'Documents')
        
        files = {}
        
        # Download WIPs file
        if 'wips_pattern' in downloads:
            files['wips'] = self.sp_client.download_latest_file(
                site_name, folder, downloads['wips_pattern'], str(self.work_dir), library
            )
        
        # Download Bills file
        if 'bills_pattern' in downloads:
            files['bills'] = self.sp_client.download_latest_file(
                site_name, folder, downloads['bills_pattern'], str(self.work_dir), library
            )
        
        # Download BoB file
        if 'bob_pattern' in downloads:
            files['bob'] = self.sp_client.download_latest_file(
                site_name, folder, downloads['bob_pattern'], str(self.work_dir), library
            )
        
        print(f"\n✓ Downloaded {len(files)} files")
        return files
    
    def prepare_bills_file(self, bills_file: str) -> tuple[str, Optional[str]]:
        """Prepare Bills file and return (prepared_file, billings_param)."""
        print("\n" + "="*60)
        print("STEP 3: Preparing Bills file")
        print("="*60)
        
        output_file = str(self.work_dir / f"Bills_prepared_{self.timestamp}.xlsx")
        invoice_month_from = self.config['analysis'].get('invoice_month_from', '2025-08')
        
        billings_param = prepare_bills_export(bills_file, output_file, invoice_month_from)
        
        return output_file, billings_param
    
    def prepare_bob_file(self, bob_file: str) -> str:
        """Prepare BoB file and return prepared file path."""
        print("\n" + "="*60)
        print("STEP 4: Preparing BoB file")
        print("="*60)
        
        output_file = str(self.work_dir / f"BoB_prepared_{self.timestamp}.xlsx")
        prepare_bob_export(bob_file, output_file)
        
        return output_file
    
    def run_engagement_analysis(self, wips_file: str, bills_file: str, 
                               bob_file: str, billings: Optional[str] = None) -> str:
        """Run the engagement analysis and return output file path."""
        print("\n" + "="*60)
        print("STEP 5: Running engagement analysis")
        print("="*60)
        
        analysis_config = self.config['analysis']
        
        # Determine output filename
        output_file = str(self.work_dir / f"Engagement_Summary_FY26_{self.timestamp}.xlsx")
        
        # Use billings from config if not provided by prepare_bills
        if billings is None:
            billings = analysis_config.get('billings', '17M')
        
        # Create temp copy of BoB to avoid lock issues
        bob_temp = str(self.work_dir / f"BoB_temp_{self.timestamp}.xlsx")
        shutil.copy(bob_file, bob_temp)
        
        # Run analysis
        try:
            run_analysis(
                input_file=wips_file,
                detail_sheet=analysis_config.get('detail_sheet', 'Detail'),
                header_row_index=analysis_config.get('header_row_index'),
                fy_start=analysis_config['fy_start'],
                fy_end=analysis_config['fy_end'],
                billings_str=billings,
                target_margin_pct=analysis_config.get('target_margin_pct', 28),
                output_file=output_file,
                bills_file=bills_file,
                bob_file=bob_temp,
                print_markdown=analysis_config.get('print_markdown', False)
            )
        finally:
            # Clean up temp file
            if Path(bob_temp).exists():
                Path(bob_temp).unlink()
        
        return output_file
    
    def upload_results(self, output_file: str) -> str:
        """Upload results to SharePoint and return web URL."""
        print("\n" + "="*60)
        print("STEP 6: Uploading results to SharePoint")
        print("="*60)
        
        uploads = self.config['uploads']
        
        web_url = self.sp_client.upload_file(
            site_name=uploads['site_name'],
            folder_path=uploads['folder_path'],
            local_file=output_file,
            library_name=uploads.get('library_name', 'Documents'),
            overwrite=True
        )
        
        # Create shareable link
        share_link = self.sp_client.create_share_link(
            site_name=uploads['site_name'],
            folder_path=uploads['folder_path'],
            filename=Path(output_file).name,
            library_name=uploads.get('library_name', 'Documents'),
            link_type='view'
        )
        
        return share_link
    
    def send_team_notification(self, share_link: str) -> None:
        """Send notification to team with results link."""
        print("\n" + "="*60)
        print("STEP 7: Sending team notification")
        print("="*60)
        
        notification = self.config.get('notification')
        if not notification or not notification.get('enabled', False):
            print("Notification disabled in config")
            return
        
        subject = notification['subject'].replace('{date}', datetime.now().strftime('%Y-%m-%d'))
        body = notification['body'].replace('{date}', datetime.now().strftime('%Y-%m-%d'))
        
        self.sp_client.send_notification(
            recipients=notification['recipients'],
            subject=subject,
            body=body,
            attachment_links=[share_link]
        )
    
    def cleanup(self) -> None:
        """Clean up temporary files."""
        print("\n" + "="*60)
        print("STEP 8: Cleaning up temporary files")
        print("="*60)
        
        if self.config.get('cleanup_work_directory', False):
            shutil.rmtree(self.work_dir)
            print(f"✓ Removed work directory: {self.work_dir}")
        else:
            print(f"Work files retained in: {self.work_dir}")
    
    def run(self) -> None:
        """Execute the complete workflow."""
        start_time = datetime.now()
        print("\n" + "="*70)
        print(f"ENGAGEMENT ANALYSIS AUTOMATION - Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        try:
            # Step 1: Setup SharePoint connection
            self.setup_sharepoint()
            
            # Step 2: Download inputs
            files = self.download_inputs()
            
            # Step 3-4: Prepare input files
            bills_prepared, billings_param = self.prepare_bills_file(files['bills'])
            bob_prepared = self.prepare_bob_file(files['bob'])
            
            # Step 5: Run analysis
            output_file = self.run_engagement_analysis(
                files['wips'], 
                bills_prepared, 
                bob_prepared,
                billings_param
            )
            
            # Step 6: Upload results
            share_link = self.upload_results(output_file)
            
            # Step 7: Notify team
            self.send_team_notification(share_link)
            
            # Step 8: Cleanup
            self.cleanup()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print("\n" + "="*70)
            print(f"✓ WORKFLOW COMPLETED SUCCESSFULLY")
            print(f"  Duration: {duration:.1f} seconds")
            print(f"  Output: {output_file}")
            print(f"  SharePoint: {share_link}")
            print("="*70)
            
        except Exception as e:
            print("\n" + "="*70)
            print(f"✗ WORKFLOW FAILED: {e}")
            print("="*70)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='End-to-end engagement analysis automation with SharePoint integration'
    )
    parser.add_argument(
        '--config',
        default='workflow_config.json',
        help='Workflow configuration file (default: workflow_config.json)'
    )
    
    args = parser.parse_args()
    
    if not Path(args.config).exists():
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        print("\nCreate a workflow_config.json file with your SharePoint and analysis settings.")
        sys.exit(1)
    
    workflow = EngagementAnalysisWorkflow(args.config)
    workflow.run()


if __name__ == '__main__':
    main()
