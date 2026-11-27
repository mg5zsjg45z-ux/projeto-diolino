import { BarChart, LineChart, PieChart } from 'echarts/charts';
import {
  AriaComponent, DataZoomComponent, GridComponent, LegendComponent, TooltipComponent,
} from 'echarts/components';
import { init, use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';

use([
  BarChart, LineChart, PieChart, AriaComponent, DataZoomComponent,
  GridComponent, LegendComponent, TooltipComponent, CanvasRenderer,
]);

export { init };
