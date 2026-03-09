"""Download figrecipe handlers: download CSV, download figure."""

import logging

from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


def handle_download_csv(request, editor):
    """Download plotted data as CSV."""
    import csv
    import io

    from figrecipe._editor._helpers import to_json_serializable

    fig = editor.fig
    if not hasattr(fig, "record") or fig.record is None:
        return JsonResponse({"error": "No recorded data available"}, status=400)

    all_data = {}
    decoration_funcs = {
        "set_xlabel",
        "set_ylabel",
        "set_title",
        "set_xlim",
        "set_ylim",
        "legend",
        "grid",
        "axhline",
        "axvline",
        "text",
        "annotate",
    }

    for ax_key, ax_record in fig.record.axes.items():
        for call in getattr(ax_record, "calls", []):
            if getattr(call, "function", "") in decoration_funcs:
                continue

            call_id = (
                getattr(call, "id", None)
                or f"{ax_key}_{getattr(call, 'function', '')}_{id(call)}"
            )
            call_data = {}

            def _extract(val):
                if isinstance(val, dict) and "data" in val:
                    return val["data"]
                if isinstance(val, list):
                    return val
                return None

            args = to_json_serializable(getattr(call, "args", []))
            kwargs = to_json_serializable(getattr(call, "kwargs", {}))

            if args:
                if len(args) >= 2:
                    x = _extract(args[0])
                    y = _extract(args[1])
                    if x:
                        call_data["x"] = x
                    if y:
                        call_data["y"] = y
                elif len(args) == 1:
                    y = _extract(args[0])
                    if y:
                        call_data["y"] = y
                        call_data["x"] = list(range(len(y)))

            for key in ["x", "y", "height", "width", "c", "s"]:
                if key in kwargs:
                    val = _extract(kwargs[key])
                    if val:
                        call_data[key] = val

            if call_data:
                all_data[call_id] = call_data

    if not all_data:
        return JsonResponse({"error": "No plot data found"}, status=400)

    output = io.StringIO()
    max_len = max(max(len(v) for v in data.values()) for data in all_data.values())
    headers = [
        f"{cid}_{key}" for cid, data in all_data.items() for key in sorted(data.keys())
    ]
    writer = csv.writer(output)
    writer.writerow(headers)

    for i in range(max_len):
        row = []
        for cid, data in all_data.items():
            for key in sorted(data.keys()):
                vals = data[key]
                row.append(vals[i] if i < len(vals) else "")
        writer.writerow(row)

    csv_bytes = output.getvalue().encode("utf-8")
    filename = "figure_data.csv"
    if editor.recipe_path:
        filename = f"{editor.recipe_path.stem}_data.csv"

    response = HttpResponse(csv_bytes, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def handle_download_fig(request, editor, fmt):
    """Download figure as png/svg/pdf at 300 DPI."""
    from figrecipe._editor._renderer import render_download

    fmt = fmt.lower()
    if fmt not in ("png", "svg", "pdf"):
        return JsonResponse({"error": f"Unsupported format: {fmt}"}, status=400)

    effective_style = editor.get_effective_style()
    content = render_download(
        editor.fig,
        fmt=fmt,
        dpi=300,
        overrides=effective_style if effective_style else None,
        dark_mode=False,
    )

    mimetype = {"png": "image/png", "svg": "image/svg+xml", "pdf": "application/pdf"}[
        fmt
    ]
    filename = f"figure.{fmt}"
    if editor.recipe_path:
        filename = f"{editor.recipe_path.stem}.{fmt}"

    response = HttpResponse(content, content_type=mimetype)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
