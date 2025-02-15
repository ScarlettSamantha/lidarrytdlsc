
import logging
import slugify
import io
import webbrowser
import pathlib 
import json

def format_debug_steps(debug_steps: list, as_html: bool = False) -> str:
    """
    Format the debug steps (list of dicts) into a table.
    
    Args:
        debug_steps (list): A list of dictionaries, each representing a scoring step.
        as_html (bool): If True, returns an HTML table; otherwise, returns plain text.
        
    Returns:
        str: The formatted debug output.
    """
    if as_html:
        table_rows = []
        table_rows.append("<table border='1' cellpadding='5' cellspacing='0'>")
        table_rows.append("<thead><tr><th>Step</th><th>Description</th><th>Change</th><th>Score</th></tr></thead>")
        table_rows.append("<tbody>")
        for idx, step in enumerate(debug_steps, start=1):
            table_rows.append(
                f"<tr>"
                f"<td>{idx}</td>"
                f"<td>{step.get('description', '')}</td>"
                f"<td>{step.get('change', '')}</td>"
                f"<td>{step.get('score', 0):.2f}</td>"
                f"</tr>"
            )
        table_rows.append("</tbody></table>")
        return "\n".join(table_rows)
    else:
        lines = []
        header = f"{'Step':<6} | {'Description':<50} | {'Change':<15} | {'Score':<10}"
        lines.append(header)
        lines.append("-" * len(header))
        for idx, step in enumerate(debug_steps, start=1):
            line = (
                f"{idx:<6} | "
                f"{step.get('description', ''):<50} | "
                f"{step.get('change', ''):<15} | "
                f"{step.get('score', 0):<10.2f}"
            )
            lines.append(line)
        return "\n".join(lines)



def write_debug_log(debug_entries: list, title: str, best_video_title: str, logger: logging.Logger) -> None:
    """
    Write the debug information into an HTML file and open it in a browser.

    Args:
        debug_entries (list): List of debug data entries.
        title (str): The original search title.
        best_video_title (str): Title of the best matching video.
        logger (logging.Logger): Logger instance for logging.
    """
    html_parts = []
    html_parts.append("<html><head><meta charset='UTF-8'><title>Debug Log</title></head><body>")
    html_parts.append(f"<h1>Debug Log for '{title}'</h1>")
    
    for entry in debug_entries:
        html_parts.append("<hr>")
        html_parts.append(f"<h2>Video ID: {entry['video_id']} - Score: {entry['score']:.2f}</h2>")
        html_parts.append("<h3>Video Data:</h3>")
        html_parts.append(f"<pre>{json.dumps(entry['video_data'], indent=4)}</pre>")
        html_parts.append("<h3>Debug Steps:</h3>")
        # Reuse the existing function to format debug steps as HTML.
        html_parts.append(format_debug_steps(entry['debug'], as_html=True))
    
    html_parts.append("</body></html>")
    html_output = "\n".join(html_parts)
    
    # Ensure the debug directory exists.
    debug_dir = pathlib.Path("/tmp/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a safe file name based on the video title.
    file_name = f"{slugify.slugify(best_video_title or 'no-match-found', lowercase=True)}.html"
    file_path = debug_dir / file_name
    
    # Write and open the debug HTML file.
    with io.open(file_path, 'w+', encoding='utf-8') as fp:
        fp.write(html_output)
    
    webbrowser.open_new_tab(file_path.as_uri())
    logger.info(f"Wrote debug log at {file_path}")
