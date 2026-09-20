/**
 * Frontend JavaScript for AI-Based Engineering Student Performance System
 * Interactive Visuals, Dynamic Chart Switching, and Search Handling
 * File: static/js/dashboard.js
 */

// Global storage for raw chart data supplied from server
window.chartRawData = window.chartRawData || {};

document.addEventListener("DOMContentLoaded", function () {
  // Auto-dismiss alert banners after 5 seconds
  const alerts = document.querySelectorAll(".alert-dismissible");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 6000);
  });

  // Responsive chart redraw on window resize
  window.addEventListener("resize", function () {
    const chartDivs = document.querySelectorAll(".plotly-graph-div");
    chartDivs.forEach(function (el) {
      if (window.Plotly && el.id) {
        Plotly.Plots.resize(el);
      }
    });
  });

  // Global search input enter key handler
  const searchInput = document.getElementById("globalStudentSearch");
  if (searchInput) {
    searchInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (query) {
          window.location.href = `/search?q=${encodeURIComponent(query)}`;
        }
      }
    });
  }

  // Initialize Sidebar Minimise / Maximise Toggle
  initSidebarToggle();
});

/**
 * Sidebar Toggle Controller (Minimise / Maximise)
 * Supports desktop collapsible mini-sidebar and mobile drawer
 */
function initSidebarToggle() {
  const wrapper = document.getElementById("appWrapper");
  const toggleBtn = document.getElementById("sidebarToggle");
  const headerToggleBtn = document.getElementById("sidebarHeaderToggle");
  const backdrop = document.getElementById("sidebarBackdrop");

  if (!wrapper) return;

  // Restore saved desktop state
  try {
    if (localStorage.getItem("sidebar_collapsed") === "true" && window.innerWidth >= 992) {
      wrapper.classList.add("sidebar-collapsed");
    }
  } catch (e) {}

  // Remove pre-render initial class smoothly
  document.documentElement.classList.remove("sidebar-init-collapsed");

  function triggerChartResize() {
    setTimeout(function () {
      const chartDivs = document.querySelectorAll(".plotly-graph-div");
      chartDivs.forEach(function (el) {
        if (window.Plotly && el.id) {
          Plotly.Plots.resize(el);
        }
      });
    }, 280);
  }

  function toggleSidebar() {
    const isMobile = window.innerWidth < 992;
    if (isMobile) {
      wrapper.classList.toggle("sidebar-open");
    } else {
      wrapper.classList.toggle("sidebar-collapsed");
      const isCollapsed = wrapper.classList.contains("sidebar-collapsed");
      try {
        localStorage.setItem("sidebar_collapsed", isCollapsed ? "true" : "false");
      } catch (e) {}
      triggerChartResize();
    }
  }

  if (toggleBtn) {
    toggleBtn.addEventListener("click", function (e) {
      e.preventDefault();
      toggleSidebar();
    });
  }

  if (headerToggleBtn) {
    headerToggleBtn.addEventListener("click", function (e) {
      e.preventDefault();
      toggleSidebar();
    });
  }

  if (backdrop) {
    backdrop.addEventListener("click", function () {
      wrapper.classList.remove("sidebar-open");
    });
  }
}

/**
 * Utility to render Plotly charts safely with dark theme aesthetics
 */
function renderPlotlyChart(elementId, figureData) {
  const container = document.getElementById(elementId);
  if (!container || !figureData) return;

  try {
    const data = typeof figureData === "string" ? JSON.parse(figureData) : figureData;
    const config = {
      responsive: true,
      displayModeBar: false
    };

    // Ensure light-theme transparency and modern font
    if (!data.layout) data.layout = {};
    data.layout.paper_bgcolor = "rgba(0,0,0,0)";
    data.layout.plot_bgcolor = "rgba(0,0,0,0)";
    if (!data.layout.font) {
      data.layout.font = { family: "Inter, sans-serif", color: "#334155" };
    }

    Plotly.newPlot(elementId, data.data, data.layout, config);
  } catch (err) {
    console.error(`Error rendering chart on #${elementId}:`, err);
  }
}

/**
 * Dynamically switches chart between Bar, Pie, and Donut with proper visual scaling
 */
function switchChartType(chartId, type, btnElement) {
  const container = document.getElementById(chartId);
  if (!container || !window.chartRawData) return;

  // Update active pill button style
  if (btnElement && btnElement.parentElement) {
    const siblings = btnElement.parentElement.querySelectorAll(".chart-toggle-btn");
    siblings.forEach(b => b.classList.remove("active"));
    btnElement.classList.add("active");
  }

  const commonLayout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", size: 12, color: "#000000", weight: 700 },
    margin: { t: 25, b: 25, l: 35, r: 20 }
  };

  const config = { responsive: true, displayModeBar: false };

  // 1. Performance Distribution Switcher
  if (chartId === "chart-performance-dist" && window.chartRawData.performance) {
    const pData = window.chartRawData.performance;
    if (type === "pie" || type === "donut") {
      const holeVal = type === "donut" ? 0.55 : 0;
      const trace = {
        labels: pData.labels,
        values: pData.values,
        type: "pie",
        hole: holeVal,
        marker: { colors: pData.colors },
        textinfo: "label+percent",
        hoverinfo: "label+value+percent",
        textfont: { color: "#ffffff", size: 13 }
      };
      const layout = {
        ...commonLayout,
        showlegend: true,
        legend: { orientation: "h", yanchor: "bottom", y: -0.2, xanchor: "center", x: 0.5, font: { color: "#000000", size: 12 } }
      };
      Plotly.react(chartId, [trace], layout, config);
    } else if (type === "bar") {
      const trace = {
        x: pData.labels,
        y: pData.values,
        type: "bar",
        marker: { color: pData.colors },
        text: pData.values,
        textposition: "auto",
        textfont: { color: "#ffffff", size: 13 },
        width: 0.45
      };
      const layout = {
        ...commonLayout,
        showlegend: false,
        xaxis: { gridcolor: "#8ca4bd", tickfont: { color: "#000000", size: 11 }, title: { text: "Predicted Category", font: { color: "#000000", size: 12 } } },
        yaxis: { gridcolor: "#8ca4bd", tickfont: { color: "#000000", size: 11 }, title: { text: "Student Count", font: { color: "#000000", size: 12 } } }
      };
      Plotly.react(chartId, [trace], layout, config);
    }
  }

  // 2. Risk Distribution Switcher
  if (chartId === "chart-risk-dist" && window.chartRawData.risk) {
    const rData = window.chartRawData.risk;
    if (type === "bar") {
      const trace = {
        x: rData.labels,
        y: rData.values,
        type: "bar",
        marker: { color: rData.colors },
        text: rData.values,
        textposition: "auto",
        width: 0.45
      };
      const layout = {
        ...commonLayout,
        showlegend: false,
        xaxis: { gridcolor: "#8ca4bd", tickfont: { color: "#000000", size: 11 }, title: { text: "Risk Classification", font: { color: "#000000", size: 12 } } },
        yaxis: { gridcolor: "#8ca4bd", tickfont: { color: "#000000", size: 11 }, title: { text: "Student Count", font: { color: "#000000", size: 12 } } }
      };
      Plotly.react(chartId, [trace], layout, config);
    } else if (type === "pie" || type === "donut") {
      const holeVal = type === "donut" ? 0.5 : 0;
      const trace = {
        labels: rData.labels,
        values: rData.values,
        type: "pie",
        hole: holeVal,
        marker: { colors: rData.colors },
        textinfo: "label+percent",
        hoverinfo: "label+value+percent",
        textfont: { color: "#ffffff", size: 13 }
      };
      const layout = {
        ...commonLayout,
        showlegend: true,
        legend: { orientation: "h", yanchor: "bottom", y: -0.2, xanchor: "center", x: 0.5, font: { color: "#000000", size: 12 } }
      };
      Plotly.react(chartId, [trace], layout, config);
    }
  }

  // 3. Department Performance Switcher
  if (chartId === "chart-dept-perf" && window.chartRawData.dept) {
    const dData = window.chartRawData.dept;
    const barmodeVal = type === "stack" ? "stack" : "group";
    const traces = dData.categories.map(c => ({
      name: c,
      x: dData.departments,
      y: dData.series[c],
      type: "bar",
      marker: { color: dData.colors[c] }
    }));
    const layout = {
      ...commonLayout,
      barmode: barmodeVal,
      xaxis: { gridcolor: "#8ca4bd", tickfont: { color: "#000000", size: 11 }, title: { text: "Department", font: { color: "#000000", size: 12 } } },
      yaxis: { gridcolor: "#8ca4bd", tickfont: { color: "#000000", size: 11 }, title: { text: "Students", font: { color: "#000000", size: 12 } } },
      legend: { orientation: "h", yanchor: "bottom", y: 1.02, xanchor: "right", x: 1, font: { color: "#000000", size: 12 } }
    };
    Plotly.react(chartId, traces, layout, config);
  }
}

/**
 * Triggers clean print/PDF export
 */
function downloadPDF() {
  window.print();
}

/**
 * Downloads a structured JSON or CSV on client side if needed
 */
function exportDataAsCSV(filename, headers, rows) {
  let csvContent = "data:text/csv;charset=utf-8," + headers.join(",") + "\n";
  rows.forEach(function (rowArray) {
    let row = rowArray.map(item => `"${String(item).replace(/"/g, '""')}"`).join(",");
    csvContent += row + "\n";
  });
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
