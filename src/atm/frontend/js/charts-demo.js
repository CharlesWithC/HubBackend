let demoOptions = {
    area: {
        series: [{
            data: [10, 8, 9, 8, 11, 16, 4, 15, 18, 21, 18, 16, 19, 14, 13, 18, 10, 10, 10, 22, 19, 20, 18, 17, 19, 13, 18, 14, 15],
        }],
        chart: {
            height: 180,
            type: 'area',
            sparkline: {
                enabled: true,
            },
        },
        colors: ['#382CDD'],
        fill: {
            type: ['solid'],
            colors: ['#EBEAFC']
        },
        stroke: {
            curve: 'straight',
            width: 2,
        },
        __variants: {
            'dark-bg': {
                colors: ['#8880EB'],
                fill: {
                    type: ['solid'],
                    colors: ['#6056E4'],
                },
            },
        },
    },

    'area-small': {
        series: [{
            data: [140, 110, 120, 140, 110, 130, 100, 120, 150, 120]
        }],
        chart: {
            height: 100,
            type: 'area',
            sparkline: {
                enabled: true
            },
        },
        colors: ['#382CDD'],
        fill: {
            type: ['solid'],
            colors: ['#EBEAFC'],
        },
        stroke: {
            width: 2,
        },
        __variants: {
            indigo: {
                colors: ['#382CDD'],
                fill: {
                    type: ['solid'],
                    colors: ['#D7D5F8'],
                },
            },
            'indigo-gradient': {
                colors: ['#382CDD'],
                fill: {
                    type: ['gradient'],
                    colors: ['#8880EB', '#EBEAFC'],
                },
            },
            blue: {
                colors: ['#2D70F5'],
                fill: {
                    type: ['solid'],
                    colors: ['#D5E2FD'],
                },
            },
            'blue-gradient': {
                colors: ['#2D70F5'],
                fill: {
                    type: ['gradient'],
                    colors: ['#81A9F9', '#EAF1FE'],
                },
            },
            green: {
                colors: ['#17BB84'],
                fill: {
                    type: ['solid'],
                    colors: ['#D1F1E6'],
                },
            },
            'green-gradient': {
                colors: ['#17BB84'],
                fill: {
                    type: ['gradient'],
                    colors: ['#74D6B5', '#E8F8F3'],
                },
            },
            orange: {
                colors: ['#F67A28'],
                fill: {
                    type: ['solid'],
                    colors: ['#FDE4D4'],
                },
            },
            'orange-gradient': {
                colors: ['#F67A28'],
                fill: {
                    type: ['gradient'],
                    colors: ['#FAAF7E', '#FEF2EA'],
                },
            },
        },
    },

    'columns-stacked': {
        series: [
            {
                data: [20, 50, 18, 50, 30, 40, 30, 40],
            },
            {
                data: [30, 0, 32, 0, 20, 10, 20, 10],
            },
        ],
        chart: {
            type: 'bar',
            height: 100,
            stacked: true,
            sparkline: {
                enabled: true,
            },
        },
        colors: ['#2D70F5', '#F1F5FB'],
        fill: {
            opacity: 1,
        },
        plotOptions: {
            bar: {
                borderRadius: 8,
            },
        },
    },

    'columns-thin': {
        series: [
            { name: 'Unique visitors', data: [99200, 68400, 72111, 65020, 62000, 71000, 84232] },
            { name: 'Total visitors', data: [112001, 92402, 86240, 97201, 72102, 102011, 98212] },
        ],
        chart: {
            type: 'bar',
            height: 300,
            toolbar: {
                show: false,
            },
        },
        stroke: {
            colors: ['transparent'],
            width: 4,
        },
        colors: ['#8128DE', '#382CDD'],
        dataLabels: {
            enabled: false,
        },
        legend: {
            show: false,
        },
        plotOptions: {
            bar: {
                borderRadius: 3,
                columnWidth: 12,
            },
        },
        xaxis: {
            categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
        },
        __variants: {
            orange: {
                colors: ['#F67A28', '#E85444'],
            },
        },
    },

    columns: {
        series: [{
            data: [
                300, 400, 200, 350, 500, 400, 300, 200, 100, 400, 500, 300, 400, 200, 100, 300,
                400, 200, 350, 500, 400, 300, 200, 100, 400, 500, 300, 400, 200, 100, 250
            ],
        }],
        chart: {
            height: 200,
            type: 'bar',
            toolbar: {
                show: false,
            },
        },
        grid: {
            show: true,
        },
        dataLabels: {
            enabled: false,
        },
        colors: ['#382CDD'],
        xaxis: {
            type: 'integer',
            categories: [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
            ],
            labels: {
                show: true,
                hideOverlappingLabels: false,
                showDuplicates: true,
                trim: false,
            },
        },
        yaxis: {
            opposite: true,
            labels: {
                show: true,
                align: 'right',
            },
        },
        plotOptions: {
            bar: {
                borderRadius: 10,
            },
        },
    },

    'radial-bar-part': {
        series: [24],
        chart: {
            type: 'radialBar',
            offsetY: -20,
            sparkline: {
                enabled: true,
            },
        },
        colors: ['#382CDD'],
        stroke: {
            lineCap: 'round',
        },
        plotOptions: {
            radialBar: {
                startAngle: -90,
                endAngle: 90,
                hollow: {
                    margin: 15,
                    size: '65%',
                },
                track: {
                    background: '#EBEAFC',
                    strokeWidth: '97%',
                    margin: 5,
                },
                dataLabels: {
                    name: {
                        show: false,
                    },
                    value: {
                        show: false,
                    },
                },
            },
        },
    },

    'radial-bar': {
        series: [54],
        chart: {
            type: 'radialBar',
            sparkline: {
                enabled: true,
            },
        },
        colors: ['#382CDD'],
        stroke: {
            lineCap: 'round',
        },
        plotOptions: {
            radialBar: {
                startAngle: -120,
                endAngle: 240,
                hollow: {
                    margin: 15,
                    size: '65%',
                },
                track: {
                    background: '#EBEAFC',
                    strokeWidth: '97%',
                    margin: 5,
                },
                dataLabels: {
                    total: {
                        show: true,
                        label: '$16,250',
                        fontSize: 24,
                        formatter: () => 'Total Payments',
                    },
                },
            },
        },
        __variants: {
            orange: {
                colors: ['#F67A28'],
                plotOptions: {
                    radialBar: {
                        startAngle: -120,
                        endAngle: 240,
                        hollow: {
                            margin: 15,
                            size: '65%',
                        },
                        track: {
                            background: '#EBEAFC',
                            strokeWidth: '97%',
                            margin: 5,
                        },
                        dataLabels: {
                            total: {
                                show: true,
                                label: '$16,250',
                                fontSize: 24,
                                formatter: () => 'Total inventory',
                            },
                        },
                    },
                },
            },
        },
    },

    donut: {
        series: [65450, 26950, 5350],
        chart: {
            type: 'donut',
            width: '100%',
            height: 240,
        },
        dataLabels: {
            enabled: false,
        },
        legend: {
            show: false,
        },
        colors: ['#2D70F5', '#382CDD', '#F67A28'],
        stroke: {
            lineCap: 'round',
        },
        plotOptions: {
            pie: {
                donut: {
                    size: '85%',
                    labels: {
                        show: true,
                        total: {
                            label: 'Total customers',
                            showAlways: true,
                            show: true,
                        },
                    },
                },
            },
            stroke: {
                colors: undefined,
            },
        },
    },
};

const renderedCharts = [];
function updateCharts() {
    if (typeof ApexCharts !== 'function') {
        return;
    }

    const chartElements = document.querySelectorAll('.chart');

    chartElements.forEach((chartElement) => {
        if (renderedCharts.includes(chartElement)) {
            return;
        }

        const type = chartElement.getAttribute('data-type');
        const variant = chartElement.getAttribute('data-variant');

        if (typeof demoOptions[type] === 'object') {
            let options = demoOptions[type];

            if (typeof options['__variants'] === 'object' && typeof options['__variants'][variant] === 'object') {
                options = { ...options, ...options['__variants'][variant] };
            }

            const chart = new ApexCharts(chartElement, options);
            chart.render();
            renderedCharts.push(chartElement);
        }
    });
}

updateCharts();
