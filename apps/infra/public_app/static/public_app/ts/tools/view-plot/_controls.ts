// UI Controls Management

import { PlotSettings } from './types';

export class ControlsManager {
    private settings: PlotSettings;
    private onSettingsChange: () => void;

    constructor(settings: PlotSettings, onSettingsChange: () => void) {
        this.settings = settings;
        this.onSettingsChange = onSettingsChange;
    }

    toggleSettingsPanel(): void {
        const panel = document.getElementById('settingsPanel');
        const button = document.getElementById('toggleSettings');
        if (!panel || !button) return;

        if (panel.style.display === 'none' || panel.style.display === '') {
            panel.style.display = 'block';
            button.textContent = '⚙️ Hide Settings';
        } else {
            panel.style.display = 'none';
            button.textContent = '⚙️ Adjust Figure Settings';
        }
    }

    updateSetting(param: string, value: string | number): void {
        let parsedValue: number | string = value;

        // Don't parse float for string values (labels)
        if (param !== 'xLabel' && param !== 'yLabel') {
            parsedValue = typeof value === 'string' ? parseFloat(value) : value;
        }

        switch(param) {
            case 'width':
                this.settings.figureWidth = parsedValue as number;
                this.settings.figureHeight = (parsedValue as number) * 0.7;
                this.updateDisplay('widthValue', (parsedValue as number).toFixed(1) + ' mm');
                this.updateDisplay('heightValue', ((parsedValue as number) * 0.7).toFixed(1) + ' mm');
                this.updateInputValue('figureHeight', (parsedValue as number) * 0.7);
                break;
            case 'lineWidth':
                this.settings.lineWidth = parsedValue as number;
                this.updateDisplay('lineWidthValue', (parsedValue as number).toFixed(2) + ' mm');
                break;
            case 'tickLength':
                this.settings.tickLength = parsedValue as number;
                this.updateDisplay('tickLengthValue', (parsedValue as number).toFixed(1) + ' mm');
                break;
            case 'tickWidth':
                this.settings.tickWidth = parsedValue as number;
                this.updateDisplay('tickWidthValue', (parsedValue as number).toFixed(2) + ' mm');
                break;
            case 'axisWidth':
                this.settings.axisWidth = parsedValue as number;
                this.updateDisplay('axisWidthValue', (parsedValue as number).toFixed(2) + ' mm');
                break;
            case 'titleFont':
                this.settings.titleFontSize = parsedValue as number;
                this.updateDisplay('titleFontValue', (parsedValue as number).toFixed(0) + ' pt');
                break;
            case 'axisFont':
                this.settings.axisFontSize = parsedValue as number;
                this.updateDisplay('axisFontValue', (parsedValue as number).toFixed(0) + ' pt');
                break;
            case 'tickFont':
                this.settings.tickFontSize = parsedValue as number;
                this.updateDisplay('tickFontValue', (parsedValue as number).toFixed(0) + ' pt');
                break;
            case 'markerSize':
                this.settings.markerSize = parsedValue as number;
                this.updateDisplay('markerSizeValue', (parsedValue as number).toFixed(1) + ' mm');
                break;
            case 'numTicks':
                this.settings.numTicks = Math.round(parsedValue as number);
                this.updateDisplay('numTicksValue', Math.round(parsedValue as number).toString());
                break;
            case 'xLabel':
                this.settings.xLabel = parsedValue as string;
                this.updateDisplay('xLabelValue', parsedValue as string);
                break;
            case 'yLabel':
                this.settings.yLabel = parsedValue as string;
                this.updateDisplay('yLabelValue', parsedValue as string);
                break;
        }

        this.onSettingsChange();
    }

    resetToDefaults(): void {
        this.updateInputAndSetting('figureWidth', 35, 'width');
        this.updateInputAndSetting('lineWidth', 0.12, 'lineWidth');
        this.updateInputAndSetting('tickLength', 0.8, 'tickLength');
        this.updateInputAndSetting('tickWidth', 0.2, 'tickWidth');
        this.updateInputAndSetting('axisWidth', 0.2, 'axisWidth');
        this.updateInputAndSetting('titleFont', 8, 'titleFont');
        this.updateInputAndSetting('axisFont', 8, 'axisFont');
        this.updateInputAndSetting('tickFont', 7, 'tickFont');
        this.updateInputAndSetting('markerSize', 0.8, 'markerSize');
        this.updateInputAndSetting('numTicks', 4, 'numTicks');
        this.updateInputAndSetting('xLabel', 'X axis', 'xLabel');
        this.updateInputAndSetting('yLabel', 'Y axis', 'yLabel');
    }

    private updateDisplay(elementId: string, value: string): void {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    private updateInputValue(elementId: string, value: number): void {
        const element = document.getElementById(elementId) as HTMLInputElement;
        if (element) {
            element.value = value.toString();
        }
    }

    private updateInputAndSetting(
        inputId: string,
        value: number | string,
        settingParam: string
    ): void {
        const element = document.getElementById(inputId) as HTMLInputElement;
        if (element) {
            element.value = value.toString();
        }
        this.updateSetting(settingParam, value);
    }
}
