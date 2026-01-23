#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statistical Plot Type Renderers
Histogram, boxplot, violin, and raster plots.
"""


def render_hist_plot(ax, df, plot_spec, style):
    """Render a histogram."""
    data_col = plot_spec.get('data_column', 'value')
    color = plot_spec.get('color', 'blue')
    bins = plot_spec.get('bins', 20)

    data = df[data_col] if data_col in df.columns else df.iloc[:, 0]

    ax.hist(data, bins=bins, color=color, alpha=0.7, edgecolor='black')

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


def render_boxplot_plot(ax, df, plot_spec, style):
    """Render a box plot."""
    # Support both single column or grouped data
    value_col = plot_spec.get('value_column', 'value')
    group_col = plot_spec.get('group_column', None)

    if group_col and group_col in df.columns:
        # Grouped boxplot
        groups = df[group_col].unique()
        data = [df[df[group_col] == g][value_col].values for g in groups]
        bp = ax.boxplot(data, labels=groups)
    else:
        # Single boxplot
        data = df[value_col] if value_col in df.columns else df.iloc[:, 0]
        bp = ax.boxplot([data])

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


def render_violin_plot(ax, df, plot_spec, style):
    """Render a violin plot."""
    value_col = plot_spec.get('value_column', 'value')
    group_col = plot_spec.get('group_column', None)

    if group_col and group_col in df.columns:
        # Grouped violin plot
        groups = df[group_col].unique()
        data = [df[df[group_col] == g][value_col].values for g in groups]
        vp = ax.violinplot(data, positions=range(len(groups)), showmeans=True)
        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels(groups)
    else:
        # Single violin plot
        data = df[value_col] if value_col in df.columns else df.iloc[:, 0]
        vp = ax.violinplot([data], showmeans=True)

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


def render_raster_plot(ax, df, plot_spec, style):
    """Render a raster plot (event plot)."""
    # Expect data in format: time_col, trial_col
    time_col = plot_spec.get('time_column', 'time')
    trial_col = plot_spec.get('trial_column', 'trial')
    color = plot_spec.get('color', 'black')

    if time_col in df.columns and trial_col in df.columns:
        # Group by trial
        trials = df[trial_col].unique()
        positions = []
        for trial in sorted(trials):
            trial_times = df[df[trial_col] == trial][time_col].values
            positions.append(trial_times)

        ax.eventplot(positions, colors=color, linewidths=0.5)
    else:
        # Fall back to simple eventplot
        times = df[time_col] if time_col in df.columns else df.iloc[:, 0]
        ax.eventplot([times], colors=color)

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


# EOF
