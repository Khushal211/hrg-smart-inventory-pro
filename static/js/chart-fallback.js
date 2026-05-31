(function () {
  if (window.Chart) return;

  function colorAt(colors, index) {
    if (Array.isArray(colors)) return colors[index % colors.length];
    return colors || "#38a169";
  }

  function clear(ctx, canvas) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "transparent";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  function setupCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(320, rect.width) * ratio;
    canvas.height = Math.max(220, rect.height) * ratio;
    const ctx = canvas.getContext("2d");
    ctx.scale(ratio, ratio);
    return { ctx, width: canvas.width / ratio, height: canvas.height / ratio };
  }

  function drawLabel(ctx, text, x, y, color) {
    ctx.fillStyle = color || "#9ba7a3";
    ctx.font = "12px Segoe UI, Arial";
    ctx.fillText(String(text), x, y);
  }

  function drawBars(canvas, config) {
    const { ctx, width, height } = setupCanvas(canvas);
    clear(ctx, { width, height });
    const labels = config.data.labels || [];
    const dataset = (config.data.datasets || [])[0] || {};
    const data = dataset.data || [];
    const max = Math.max(1, ...data);
    const horizontal = config.options && config.options.indexAxis === "y";
    const pad = 34;

    if (horizontal) {
      const rowHeight = Math.max(22, (height - pad * 1.5) / Math.max(1, data.length));
      data.forEach((value, index) => {
        const y = pad + index * rowHeight;
        const barWidth = ((width - 170) * value) / max;
        drawLabel(ctx, labels[index] || "", 12, y + 14);
        ctx.fillStyle = colorAt(dataset.backgroundColor, index);
        ctx.fillRect(150, y, barWidth, 14);
        drawLabel(ctx, Math.round(value), 158 + barWidth, y + 12, "#f1f5f2");
      });
      return;
    }

    const barWidth = Math.max(18, (width - pad * 2) / Math.max(1, data.length) - 10);
    data.forEach((value, index) => {
      const barHeight = ((height - pad * 2) * value) / max;
      const x = pad + index * (barWidth + 10);
      const y = height - pad - barHeight;
      ctx.fillStyle = colorAt(dataset.backgroundColor, index);
      ctx.fillRect(x, y, barWidth, barHeight);
      drawLabel(ctx, labels[index] || "", x, height - 10);
    });
  }

  function drawLine(canvas, config) {
    const { ctx, width, height } = setupCanvas(canvas);
    clear(ctx, { width, height });
    const labels = config.data.labels || [];
    const datasets = config.data.datasets || [];
    const allValues = datasets.flatMap((dataset) => dataset.data || []);
    const max = Math.max(1, ...allValues);
    const pad = 34;

    datasets.forEach((dataset, dIndex) => {
      const data = dataset.data || [];
      ctx.beginPath();
      data.forEach((value, index) => {
        const x = pad + (index * (width - pad * 2)) / Math.max(1, data.length - 1);
        const y = height - pad - ((height - pad * 2) * value) / max;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = dataset.borderColor || colorAt(["#3182ce", "#38a169", "#d69e2e"], dIndex);
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    labels.forEach((label, index) => {
      const x = pad + (index * (width - pad * 2)) / Math.max(1, labels.length - 1);
      drawLabel(ctx, label, x - 18, height - 10);
    });
  }

  function drawDoughnut(canvas, config) {
    const { ctx, width, height } = setupCanvas(canvas);
    clear(ctx, { width, height });
    const labels = config.data.labels || [];
    const dataset = (config.data.datasets || [])[0] || {};
    const data = dataset.data || [];
    const total = data.reduce((sum, value) => sum + Number(value || 0), 0) || 1;
    const radius = Math.min(width, height) * 0.28;
    const cx = width * 0.34;
    const cy = height * 0.46;
    let start = -Math.PI / 2;

    data.forEach((value, index) => {
      const angle = (value / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, start, start + angle);
      ctx.closePath();
      ctx.fillStyle = colorAt(dataset.backgroundColor, index);
      ctx.fill();
      start += angle;
    });

    ctx.beginPath();
    ctx.arc(cx, cy, radius * 0.55, 0, Math.PI * 2);
    ctx.fillStyle = "#171a1f";
    ctx.fill();

    labels.slice(0, 7).forEach((label, index) => {
      const y = 28 + index * 22;
      ctx.fillStyle = colorAt(dataset.backgroundColor, index);
      ctx.fillRect(width * 0.62, y - 10, 10, 10);
      drawLabel(ctx, label, width * 0.62 + 16, y);
    });
  }

  window.Chart = class FallbackChart {
    constructor(canvas, config) {
      this.canvas = canvas;
      this.config = config;
      this.render();
    }

    render() {
      if (!this.canvas || !this.canvas.getContext) return;
      if (this.config.type === "doughnut") drawDoughnut(this.canvas, this.config);
      else if (this.config.type === "line") drawLine(this.canvas, this.config);
      else drawBars(this.canvas, this.config);
    }

    destroy() {}
  };
  window.Chart.__fallback = true;
})();
