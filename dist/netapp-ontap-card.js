class NetAppOntapCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.mode = 'diagram'; // 'diagram', 'list', 'metrics', 'hybrid'
    this.selectedNode = null;
    this.selectedVolume = null;
    this.selectedAggregate = null;
    this.drillDownLevel = 'cluster'; // 'cluster', 'node', 'aggregate', 'volume'
    this.drillDownId = null;
  }

  static getStubConfig() {
    return {
      entity: 'sensor.netapp_ontap_topology',
      title: 'NetApp ONTAP Cluster'
    };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('Please define a NetApp ONTAP topology entity');
    }
    this.config = config;
  }

  set hass(hass) {
    this._hass = hass;
    const entityId = this.config.entity;
    const stateObj = hass.states[entityId];

    // Read attributes or fallback to mock data for presentation
    if (stateObj && stateObj.attributes && stateObj.attributes.cluster) {
      const clusterRaw = { ...stateObj.attributes.cluster };
      if (clusterRaw.version && typeof clusterRaw.version === 'object') {
        clusterRaw.version = clusterRaw.version.full || `${clusterRaw.version.generation}.${clusterRaw.version.major}.${clusterRaw.version.minor}`;
      }
      this.data = {
        cluster: clusterRaw,
        nodes: (stateObj.attributes.nodes || []).map(n => ({
          ...n,
          version: typeof n.version === 'object' && n.version ? (n.version.full || `${n.version.generation}.${n.version.major}`) : n.version
        })),
        aggregates: stateObj.attributes.aggregates || [],
        volumes: stateObj.attributes.volumes || [],
        interfaces: stateObj.attributes.interfaces || [],
        events: stateObj.attributes.events || [],
        fc_ports: stateObj.attributes.fc_ports || [],
        ethernet_ports: stateObj.attributes.ethernet_ports || []
      };
    } else {
      // Load rich Mock Data for WOW effect in preview/demo
      this.data = this.getMockData();
    }

    this.render();
  }

  getMockData() {
    return {
      cluster: {
        name: 'ONTAP-Cluster-01',
        uuid: 'cluster-uuid-12345',
        version: '9.10.1P4',
        healthy: true,
        location: 'Data Center A'
      },
      nodes: [
        { uuid: 'node-1', name: 'ontap-node-01', state: 'healthy', version: '9.10.1P4', model: 'FAS8300' },
        { uuid: 'node-2', name: 'ontap-node-02', state: 'healthy', version: '9.10.1P4', model: 'FAS8300' }
      ],
      aggregates: [
        { uuid: 'aggr-1', name: 'aggr1_node1', state: 'online', space: { size: 10995116277760, used: 7696581394432 }, home_node: { name: 'ontap-node-01' } },
        { uuid: 'aggr-2', name: 'aggr2_node2', state: 'online', space: { size: 10995116277760, used: 4398046511104 }, home_node: { name: 'ontap-node-02' } }
      ],
      volumes: [
        { uuid: 'vol-1', name: 'vol_db_prod', state: 'online', space: { size: 5497558138880, used: 4123168604160 }, aggregate: { name: 'aggr1_node1' }, metric: { iops: { total: 4250 }, latency: { total: 850 }, throughput: { total: 78643200 } } },
        { uuid: 'vol-2', name: 'vol_san_vmware', state: 'online', space: { size: 3298534883328, used: 1649267441664 }, aggregate: { name: 'aggr1_node1' }, metric: { iops: { total: 1800 }, latency: { total: 1200 }, throughput: { total: 45097152 } } },
        { uuid: 'vol-3', name: 'vol_nfs_shared', state: 'online', space: { size: 2199023255552, used: 1979120929996 }, aggregate: { name: 'aggr2_node2' }, metric: { iops: { total: 620 }, latency: { total: 3400 }, throughput: { total: 12582912 } } }
      ],
      interfaces: [
        { name: 'lif_iscsi_1', state: 'up', ip: { address: '192.168.10.11' } },
        { name: 'lif_mgmt', state: 'up', ip: { address: '192.168.1.50' } }
      ],
      events: [
        { time: '2026-06-12T07:15:00Z', message: 'Volume vol_nfs_shared is reaching 90% capacity threshold', severity: 'warning' }
      ]
    };
  }

  render() {
    if (!this.data) return;

    const styles = `
      :host {
        --primary-color: #2196f3;
        --accent-color: #00e5ff;
        --bg-card: rgba(30, 30, 40, 0.75);
        --bg-header: rgba(40, 40, 55, 0.9);
        --border-glass: 1px solid rgba(255, 255, 255, 0.08);
        --text-main: #f5f5f7;
        --text-sub: #a1a1a6;
        --color-healthy: #00e676;
        --color-warning: #ffea00;
        --color-danger: #ff1744;
        font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        display: block;
        border-radius: 16px;
        background: var(--bg-card);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: var(--border-glass);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        overflow: hidden;
        color: var(--text-main);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
      }

      .card-header {
        background: var(--bg-header);
        padding: 16px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: var(--border-glass);
      }

      .title-section h3 {
        margin: 0;
        font-size: 1.15rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, #fff 0%, #a1a1a6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }

      .title-section span {
        font-size: 0.8rem;
        color: var(--text-sub);
      }

      .view-modes {
        display: flex;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 20px;
        padding: 2px;
        border: var(--border-glass);
      }

      .mode-btn {
        background: transparent;
        border: none;
        color: var(--text-sub);
        padding: 6px 12px;
        font-size: 0.8rem;
        font-weight: 500;
        border-radius: 18px;
        cursor: pointer;
        transition: all 0.2s;
      }

      .mode-btn.active {
        background: var(--primary-color);
        color: #fff;
        box-shadow: 0 2px 10px rgba(33, 150, 243, 0.4);
      }

      .card-content {
        padding: 20px;
      }

      /* Topology Diagram Styling */
      .topology-container {
        display: flex;
        flex-direction: column;
        gap: 20px;
        align-items: center;
        position: relative;
      }

      .cluster-node-visual {
        background: linear-gradient(135deg, rgba(33, 150, 243, 0.15) 0%, rgba(0, 229, 255, 0.05) 100%);
        border: 1px solid rgba(33, 150, 243, 0.3);
        border-radius: 12px;
        padding: 12px 24px;
        text-align: center;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: transform 0.2s;
      }

      .cluster-node-visual:hover {
        transform: translateY(-2px);
        border-color: var(--accent-color);
      }

      .diagram-row {
        display: flex;
        justify-content: center;
        gap: 40px;
        width: 100%;
        flex-wrap: wrap;
      }

      .schematic-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 16px;
        width: 260px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        position: relative;
        transition: all 0.2s;
        cursor: pointer;
      }

      .schematic-card:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(255, 255, 255, 0.15);
        transform: translateY(-2px);
      }

      .schematic-card.selected {
        border-color: var(--primary-color);
        box-shadow: 0 0 15px rgba(33, 150, 243, 0.25);
      }

      .card-title {
        font-weight: 600;
        font-size: 0.95rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .badge {
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 10px;
        font-weight: 600;
      }

      .badge.healthy { background: rgba(0, 230, 118, 0.15); color: var(--color-healthy); }
      .badge.warning { background: rgba(255, 234, 0, 0.15); color: var(--color-warning); }

      .progress-bar-container {
        width: 100%;
        background: rgba(255,255,255,0.08);
        height: 6px;
        border-radius: 3px;
        overflow: hidden;
      }

      .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--accent-color) 100%);
        border-radius: 3px;
      }

      .progress-bar.warning {
        background: linear-gradient(90deg, #ff9800 0%, #ffc107 100%);
      }

      .info-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: var(--text-sub);
      }

      /* Sub items inside aggregates / volumes list */
      .sub-items-container {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 8px;
        border-top: 1px solid rgba(255,255,255,0.06);
        padding-top: 8px;
      }

      .sub-item {
        background: rgba(0, 0, 0, 0.2);
        padding: 8px;
        border-radius: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        transition: background 0.2s;
      }

      .sub-item:hover {
        background: rgba(255,255,255,0.05);
      }

      /* Hover Tooltips / Details Overlay */
      .details-panel {
        background: rgba(20, 20, 30, 0.95);
        border: var(--border-glass);
        border-radius: 12px;
        padding: 16px;
        margin-top: 20px;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
      }

      .actions-container {
        display: flex;
        gap: 12px;
        margin-top: 12px;
      }

      .action-btn {
        background: rgba(255, 255, 255, 0.08);
        border: var(--border-glass);
        color: var(--text-main);
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
      }

      .action-btn:hover {
        background: var(--primary-color);
        box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
      }

      /* Metrics Dashboard View */
      .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
      }

      .metric-card {
        background: rgba(0,0,0,0.25);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
      }

      .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--accent-color);
        margin: 8px 0;
      }

      .back-btn {
        background: transparent;
        border: none;
        color: var(--text-sub);
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 0.85rem;
        margin-bottom: 12px;
      }

      .back-btn:hover {
        color: var(--text-main);
      }
    `;

    // Render HTML content based on current view mode and drill down state
    this.shadowRoot.innerHTML = `
      <style>${styles}</style>
      <div class="card-header">
        <div class="title-section">
          <h3>
            <ha-icon icon="mdi:nas"></ha-icon>
            ${this.config.title || 'NetApp ONTAP Cluster'}
          </h3>
          <span>${this.data.cluster.version} &bull; ${this.data.cluster.location || 'Local'}</span>
        </div>
        <div class="view-modes">
          <button class="mode-btn ${this.mode === 'diagram' ? 'active' : ''}" id="mode-diagram">Topology</button>
          <button class="mode-btn ${this.mode === 'list' ? 'active' : ''}" id="mode-list">List</button>
          <button class="mode-btn ${this.mode === 'metrics' ? 'active' : ''}" id="mode-metrics">Metrics</button>
        </div>
      </div>
      <div class="card-content">
        ${this.renderBody()}
      </div>
    `;

    this.attachEventListeners();
  }

  renderBody() {
    if (this.mode === 'diagram') {
      return this.renderDiagram();
    } else if (this.mode === 'list') {
      return this.renderList();
    } else if (this.mode === 'metrics') {
      return this.renderMetrics();
    }
    return '';
  }

  renderDiagram() {
    if (this.drillDownLevel === 'cluster') {
      return `
        <div class="topology-container">
          <div class="cluster-node-visual" id="cluster-root">
            <div style="font-weight: 700;">${this.data.cluster.name}</div>
            <div style="font-size: 0.8rem; color: var(--text-sub);">Cluster Health: ${this.data.cluster.healthy ? 'Healthy' : 'Degraded'}</div>
          </div>
          
          <div style="color: var(--text-sub); font-size: 0.8rem; margin: 5px 0;">Click elements to drill down / interact</div>

          <div class="diagram-row">
            ${this.data.nodes.map(node => `
              <div class="schematic-card" id="btn-drill-node-${node.uuid}">
                <div class="card-title">
                  <span>Node: ${node.name}</span>
                  <span class="badge healthy">${node.state}</span>
                </div>
                <div class="info-row">
                  <span>Model:</span>
                  <span>${node.model}</span>
                </div>
                <div class="info-row">
                  <span>Aggregates:</span>
                  <span>${this.data.aggregates.filter(a => a.home_node.name === node.name).length}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    if (this.drillDownLevel === 'node') {
      const node = this.data.nodes.find(n => n.uuid === this.drillDownId);
      const nodeAggrs = this.data.aggregates.filter(a => a.home_node.name === node.name);

      return `
        <button class="back-btn" id="drill-back-cluster">
          <ha-icon icon="mdi:arrow-left"></ha-icon> Back to Cluster View
        </button>
        <div class="topology-container">
          <div class="cluster-node-visual">
            <div style="font-weight: 700;">Node: ${node.name}</div>
            <div style="font-size: 0.8rem; color: var(--text-sub);">Aggregates managed by this node</div>
          </div>

          <div class="diagram-row">
            ${nodeAggrs.map(aggr => {
              const pct = Math.round((aggr.space.used / aggr.space.size) * 100);
              const warningClass = pct > 85 ? 'warning' : '';
              return `
                <div class="schematic-card" id="btn-drill-aggr-${aggr.uuid}">
                  <div class="card-title">
                    <span>Aggr: ${aggr.name}</span>
                    <span class="badge healthy">${aggr.state}</span>
                  </div>
                  <div class="progress-bar-container">
                    <div class="progress-bar ${warningClass}" style="width: ${pct}%"></div>
                  </div>
                  <div class="info-row">
                    <span>Used:</span>
                    <span>${pct}% of ${this.formatBytes(aggr.space.size)}</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    if (this.drillDownLevel === 'aggregate') {
      const aggr = this.data.aggregates.find(a => a.uuid === this.drillDownId);
      const aggrVols = this.data.volumes.filter(v => v.aggregate.name === aggr.name);

      return `
        <button class="back-btn" id="drill-back-node">
          <ha-icon icon="mdi:arrow-left"></ha-icon> Back to Node View
        </button>
        <div class="topology-container">
          <div class="cluster-node-visual">
            <div style="font-weight: 700;">Aggregate: ${aggr.name}</div>
            <div style="font-size: 0.8rem; color: var(--text-sub);">Volumes on this Aggregate</div>
          </div>

          <div class="diagram-row">
            ${aggrVols.map(vol => {
              const pct = Math.round((vol.space.used / vol.space.size) * 100);
              const warningClass = pct > 85 ? 'warning' : '';
              return `
                <div class="schematic-card" id="btn-vol-detail-${vol.uuid}">
                  <div class="card-title">
                    <span>Vol: ${vol.name}</span>
                    <span class="badge healthy">${vol.state}</span>
                  </div>
                  <div class="progress-bar-container">
                    <div class="progress-bar ${warningClass}" style="width: ${pct}%"></div>
                  </div>
                  <div class="info-row">
                    <span>Capacity:</span>
                    <span>${pct}% / ${this.formatBytes(vol.space.size)}</span>
                  </div>
                  <div class="info-row">
                    <span>IOPS:</span>
                    <span>${vol.metric.iops.total}</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
          ${this.renderDetailPanel()}
        </div>
      `;
    }

    return '';
  }

  renderList() {
    return `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div style="font-weight: 600; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px;">Volumes Detail List</div>
        ${this.data.volumes.map(vol => {
          const pct = Math.round((vol.space.used / vol.space.size) * 100);
          return `
            <div class="sub-item" style="padding: 12px; cursor: pointer;" id="btn-vol-detail-${vol.uuid}">
              <div>
                <div style="font-weight: 600;">${vol.name}</div>
                <div style="font-size: 0.75rem; color: var(--text-sub);">Aggregate: ${vol.aggregate.name} &bull; State: ${vol.state}</div>
              </div>
              <div style="text-align: right;">
                <div>${pct}% (${this.formatBytes(vol.space.used)} / ${this.formatBytes(vol.space.size)})</div>
                <div style="font-size: 0.75rem; color: var(--accent-color);">${vol.metric.iops.total} IOPS &bull; ${vol.metric.latency.total / 1000} ms</div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
      ${this.renderDetailPanel()}
    `;
  }

  renderMetrics() {
    const totalIOPS = this.data.volumes.reduce((sum, v) => sum + v.metric.iops.total, 0);
    const avgLatency = this.data.volumes.length ? (this.data.volumes.reduce((sum, v) => sum + v.metric.latency.total, 0) / this.data.volumes.length) : 0;
    const totalThroughput = this.data.volumes.reduce((sum, v) => sum + v.metric.throughput.total, 0);

    return `
      <div class="metrics-grid">
        <div class="metric-card">
          <ha-icon icon="mdi:speedometer" style="color: var(--primary-color); font-size: 24px;"></ha-icon>
          <div style="font-size: 0.8rem; color: var(--text-sub); margin-top: 6px;">Total IOPS</div>
          <div class="metric-value">${totalIOPS}</div>
        </div>
        <div class="metric-card">
          <ha-icon icon="mdi:clock-fast" style="color: #ff9800; font-size: 24px;"></ha-icon>
          <div style="font-size: 0.8rem; color: var(--text-sub); margin-top: 6px;">Avg Latency</div>
          <div class="metric-value">${(avgLatency / 1000).toFixed(2)} ms</div>
        </div>
        <div class="metric-card">
          <ha-icon icon="mdi:download" style="color: var(--color-healthy); font-size: 24px;"></ha-icon>
          <div style="font-size: 0.8rem; color: var(--text-sub); margin-top: 6px;">Total Throughput</div>
          <div class="metric-value">${(totalThroughput / (1024 * 1024)).toFixed(1)} MB/s</div>
        </div>
      </div>

      <div style="margin-top: 20px;">
        <div style="font-weight: 600; margin-bottom: 10px;">Recent EMS System Events</div>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${this.data.events.map(ev => `
            <div class="sub-item" style="border-left: 3px solid var(--color-warning);">
              <span style="font-size: 0.8rem;">${ev.message}</span>
              <span style="font-size: 0.7rem; color: var(--text-sub); white-space: nowrap;">${new Date(ev.time).toLocaleTimeString()}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderDetailPanel() {
    if (!this.selectedVolume) return '';
    const vol = this.data.volumes.find(v => v.uuid === this.selectedVolume);
    if (!vol) return '';

    const pct = Math.round((vol.space.used / vol.space.size) * 100);

    return `
      <div class="details-panel">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; margin-bottom: 12px;">
          <span style="font-weight: 700; font-size: 1rem;">Volume Control: ${vol.name}</span>
          <ha-icon icon="mdi:close" id="btn-close-detail" style="cursor: pointer;"></ha-icon>
        </div>
        <div class="metrics-grid" style="margin-bottom: 15px; grid-template-columns: 1fr 1fr;">
          <div class="info-row"><span>State:</span><span style="font-weight: 600; color: var(--color-healthy);">${vol.state}</span></div>
          <div class="info-row"><span>Capacity:</span><span>${pct}% / ${this.formatBytes(vol.space.size)}</span></div>
          <div class="info-row"><span>IOPS:</span><span>${vol.metric.iops.total}</span></div>
          <div class="info-row"><span>Latency:</span><span>${(vol.metric.latency.total / 1000).toFixed(2)} ms</span></div>
        </div>
        
        <div class="actions-container">
          <button class="action-btn" id="btn-snap-action" style="background: rgba(33, 150, 243, 0.2); border-color: var(--primary-color);">
            <ha-icon icon="mdi:camera"></ha-icon> Create Snapshot
          </button>
          <button class="action-btn" id="btn-toggle-action" style="${vol.state === 'online' ? 'background: rgba(255, 23, 68, 0.2); border-color: var(--color-danger);' : 'background: rgba(0, 230, 118, 0.2); border-color: var(--color-healthy);'}">
            <ha-icon icon="mdi:power"></ha-icon> ${vol.state === 'online' ? 'Take Offline' : 'Bring Online'}
          </button>
        </div>
      </div>
    `;
  }

  attachEventListeners() {
    // Mode toggling
    const modeDiagram = this.shadowRoot.getElementById('mode-diagram');
    const modeList = this.shadowRoot.getElementById('mode-list');
    const modeMetrics = this.shadowRoot.getElementById('mode-metrics');

    if (modeDiagram) modeDiagram.addEventListener('click', () => { this.mode = 'diagram'; this.render(); });
    if (modeList) modeList.addEventListener('click', () => { this.mode = 'list'; this.render(); });
    if (modeMetrics) modeMetrics.addEventListener('click', () => { this.mode = 'metrics'; this.render(); });

    // Drill down actions
    this.data.nodes.forEach(node => {
      const el = this.shadowRoot.getElementById(`btn-drill-node-${node.uuid}`);
      if (el) el.addEventListener('click', () => {
        this.drillDownLevel = 'node';
        this.drillDownId = node.uuid;
        this.render();
      });
    });

    const backCluster = this.shadowRoot.getElementById('drill-back-cluster');
    if (backCluster) backCluster.addEventListener('click', () => {
      this.drillDownLevel = 'cluster';
      this.drillDownId = null;
      this.render();
    });

    this.data.aggregates.forEach(aggr => {
      const el = this.shadowRoot.getElementById(`btn-drill-aggr-${aggr.uuid}`);
      if (el) el.addEventListener('click', () => {
        this.drillDownLevel = 'aggregate';
        this.drillDownId = aggr.uuid;
        this.render();
      });
    });

    const backNode = this.shadowRoot.getElementById('drill-back-node');
    if (backNode) backNode.addEventListener('click', () => {
      // Find the node belonging to the current aggregate
      const aggr = this.data.aggregates.find(a => a.uuid === this.drillDownId);
      const node = this.data.nodes.find(n => n.name === aggr.home_node.name);
      this.drillDownLevel = 'node';
      this.drillDownId = node.uuid;
      this.render();
    });

    // Volume details selection
    this.data.volumes.forEach(vol => {
      const el = this.shadowRoot.getElementById(`btn-vol-detail-${vol.uuid}`);
      if (el) el.addEventListener('click', () => {
        this.selectedVolume = vol.uuid;
        this.render();
      });
    });

    const closeDetail = this.shadowRoot.getElementById('btn-close-detail');
    if (closeDetail) closeDetail.addEventListener('click', () => {
      this.selectedVolume = null;
      this.render();
    });

    // Write Action Triggers with Confirmation Dialogs
    const snapAction = this.shadowRoot.getElementById('btn-snap-action');
    if (snapAction) {
      snapAction.addEventListener('click', () => {
        const vol = this.data.volumes.find(v => v.uuid === this.selectedVolume);
        if (confirm(`Are you sure you want to trigger snapshot creation on volume ${vol.name}?`)) {
          this.callHAService('button', 'press', { entity_id: `button.netapp_volume_${vol.name.toLowerCase()}_create_snapshot` });
          alert(`Snapshot request submitted for ${vol.name}.`);
        }
      });
    }

    const toggleAction = this.shadowRoot.getElementById('btn-toggle-action');
    if (toggleAction) {
      toggleAction.addEventListener('click', () => {
        const vol = this.data.volumes.find(v => v.uuid === this.selectedVolume);
        const nextState = vol.state === 'online' ? 'offline' : 'online';
        if (confirm(`CAUTION: Are you sure you want to change volume ${vol.name} state to ${nextState.toUpperCase()}?`)) {
          const serviceName = vol.state === 'online' ? 'turn_off' : 'turn_on';
          this.callHAService('switch', serviceName, { entity_id: `switch.netapp_volume_${vol.name.toLowerCase()}_enabled` });
          alert(`Volume state change request submitted.`);
        }
      });
    }
  }

  callHAService(domain, service, serviceData) {
    if (this._hass) {
      this._hass.callService(domain, service, serviceData);
    } else {
      console.log('Mock HA Service call:', domain, service, serviceData);
    }
  }

  formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }

  getCardSize() {
    return 4;
  }
}

customElements.define('netapp-ontap-card', NetAppOntapCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'netapp-ontap-card',
  name: 'NetApp ONTAP Cluster Card',
  description: 'Interactive visualization of NetApp storage systems, aggregates, and volumes with status overlay.',
  preview: true
});
