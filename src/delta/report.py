import json
import os
from src.delta.model import DeltaReport

def generate_report(report: DeltaReport, output_dir: str = "data/reports"):
    """
    Generates both a human-readable Markdown report and a machine-parseable JSON report.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. JSON Report (Machine Parseable)
    json_path = os.path.join(output_dir, f"{report.base_pid}_to_{report.revised_pid}_delta.json")
    with open(json_path, 'w') as f:
        f.write(report.model_dump_json(indent=2))
        
    # 2. Markdown Report (Human Readable & Retrievable by LLM)
    md_path = os.path.join(output_dir, f"{report.base_pid}_to_{report.revised_pid}_delta.md")
    
    summary = report.summary_counts
    
    md_lines = [
        f"# Delta Report: {report.base_pid} ➔ {report.revised_pid}",
        "",
        "## Summary",
        f"- **Added:** {summary['added']}",
        f"- **Removed:** {summary['removed']}",
        f"- **Modified:** {summary['modified']}",
        "",
        "## Detailed Changes",
        ""
    ]
    
    # Group by page
    changes_by_page = {}
    for c in report.changes:
        changes_by_page.setdefault(c.page_number, []).append(c)
        
    for page, changes in sorted(changes_by_page.items()):
        md_lines.append(f"### Page {page}")
        for c in changes:
            icon = "🟢" if c.change_type.value == "added" else "🔴" if c.change_type.value == "removed" else "🟡"
            md_lines.append(f"* {icon} **[{c.change_type.value.upper()}]** {c.description} (Confidence: {c.confidence.value})")
        md_lines.append("")
        
    with open(md_path, 'w') as f:
        f.write("\n".join(md_lines))
        
    return json_path, md_path
