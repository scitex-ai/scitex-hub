"""Datatable figrecipe handlers: data, plot, import. WORKFLOW 2."""

import json
import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def handle_datatable_data(request, editor):
    from figrecipe._editor._helpers import to_json_serializable

    if not hasattr(editor.fig, "record") or not editor.fig.record:
        return JsonResponse({"columns": [], "data": [], "source": "empty"})

    record = editor.fig.record
    columns = []
    data_rows = []

    for ax_key, ax_record in record.axes.items():
        for call in getattr(ax_record, "calls", []):
            kwargs = getattr(call, "kwargs", {})
            args = getattr(call, "args", [])
            func = getattr(call, "function", "")

            x_data = kwargs.get("x") or (args[0] if len(args) > 0 else None)
            y_data = kwargs.get("y") or (args[1] if len(args) > 1 else None)

            if x_data is not None and y_data is not None:
                call_id = (
                    getattr(call, "call_id", None) or getattr(call, "id", None) or func
                )
                x_col = f"{call_id}_x"
                y_col = f"{call_id}_y"
                if x_col not in columns:
                    columns.extend([x_col, y_col])
                x_list = to_json_serializable(x_data)
                y_list = to_json_serializable(y_data)
                if isinstance(x_list, list) and isinstance(y_list, list):
                    for i, (xv, yv) in enumerate(zip(x_list, y_list)):
                        while len(data_rows) <= i:
                            data_rows.append({})
                        data_rows[i][x_col] = xv
                        data_rows[i][y_col] = yv

    return JsonResponse({"columns": columns, "data": data_rows, "source": "record"})


def handle_datatable_plot(request, editor):
    """Plot from datatable column selections."""
    from figrecipe._editor._helpers import render_with_overrides

    from ._core import _regen_hitmap

    data = json.loads(request.body) if request.body else {}
    plot_data = data.get("data", {})
    columns = data.get("columns", [])
    plot_type = data.get("plot_type", "line")
    target_axis = data.get("target_axis")

    if not columns:
        return JsonResponse({"error": "Please select columns to plot"}, status=400)
    if not plot_data:
        return JsonResponse(
            {"error": "No data available. Drop CSV/TSV data first."}, status=400
        )
    if not any(len(plot_data.get(col, [])) > 0 for col in columns):
        return JsonResponse({"error": "Selected columns have no data"}, status=400)

    try:
        mpl_fig = editor.fig.fig if hasattr(editor.fig, "fig") else editor.fig
        axes = mpl_fig.get_axes()

        if target_axis is not None and target_axis < len(axes):
            ax = axes[target_axis]
        else:
            n_axes = len(axes)
            if n_axes == 0:
                ax = mpl_fig.add_subplot(111)
            else:
                current_w, current_h = mpl_fig.get_size_inches()
                mpl_fig.set_size_inches(current_w + 60 / 25.4, current_h)
                n_cols = n_axes + 1
                margin, spacing = 0.08, 0.05
                panel_w = (1 - 2 * margin - (n_cols - 1) * spacing) / n_cols
                for i, old_ax in enumerate(axes):
                    old_ax.set_position(
                        [margin + i * (panel_w + spacing), 0.15, panel_w, 0.75]
                    )
                ax = mpl_fig.add_axes(
                    [margin + n_axes * (panel_w + spacing), 0.15, panel_w, 0.75]
                )

        from figrecipe._editor._datatable_plot_handlers import dispatch_plot

        try:
            dispatch_plot(ax, plot_type, plot_data, columns)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

        if hasattr(editor, "_initial_axes_positions") and hasattr(
            editor, "_capture_axes_positions"
        ):
            editor._initial_axes_positions = editor._capture_axes_positions()

        img, bboxes, size = render_with_overrides(
            editor.fig, editor.get_effective_style(), editor.dark_mode
        )
        _regen_hitmap(editor, size)

        return JsonResponse(
            {
                "success": True,
                "image": img,
                "bboxes": bboxes,
                "img_size": {"width": size[0], "height": size[1]},
            }
        )
    except Exception as e:
        logger.exception("[Vis] datatable_plot failed")
        return JsonResponse({"error": f"Plot error: {type(e).__name__}"}, status=500)


def handle_datatable_import(request, editor):
    """Import CSV/TSV/JSON data into the datatable."""
    import csv
    import io
    import json as _json

    data = json.loads(request.body) if request.body else {}
    content = data.get("content", "")
    fmt = data.get("format", "csv").lower()

    try:
        if fmt == "json":
            parsed = _json.loads(content)
            if isinstance(parsed, list):
                if not parsed:
                    return JsonResponse({"columns": [], "rows": []})
                headers = list(parsed[0].keys())
                rows = [[obj.get(h) for h in headers] for obj in parsed]
            elif isinstance(parsed, dict):
                headers = list(parsed.keys())
                max_len = max(
                    len(v) if isinstance(v, list) else 1 for v in parsed.values()
                )
                rows = []
                for i in range(max_len):
                    row = []
                    for h in headers:
                        v = parsed[h]
                        row.append(
                            v[i]
                            if isinstance(v, list) and i < len(v)
                            else (v if i == 0 else None)
                        )
                    rows.append(row)
            else:
                return JsonResponse({"error": "Invalid JSON structure"}, status=400)
        else:
            delimiter = "\t" if fmt == "tsv" else ","
            reader = csv.reader(io.StringIO(content), delimiter=delimiter)
            lines = list(reader)
            if not lines:
                return JsonResponse({"columns": [], "rows": []})
            headers = lines[0]
            rows = []
            for line in lines[1:]:
                row = []
                for val in line:
                    try:
                        row.append(float(val))
                    except ValueError:
                        row.append(val)
                rows.append(row)

        columns = []
        for i, name in enumerate(headers):
            values = [row[i] for row in rows if i < len(row) and row[i] is not None]
            is_numeric = all(isinstance(v, (int, float)) for v in values)
            columns.append(
                {
                    "name": name,
                    "type": "numeric" if is_numeric else "string",
                    "index": i,
                }
            )

        return JsonResponse({"columns": columns, "rows": rows})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
