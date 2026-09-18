import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import type { GraphData } from '../api';

const EDGE_COLORS: Record<string, string> = {
  conflicts: '#ef4444',
  supports: '#22c55e',
  duplicates: '#eab308',
  unaddressed: '#64748b',
  policy_conflict: '#a855f7',
};

const NODE_COLORS: Record<string, string> = {
  obligation: '#06b6d4',
  requirement: '#d946ef',
};

const EDGE_LABELS: Record<string, string> = {
  conflicts: 'Conflicts With',
  supports: 'Supports',
  duplicates: 'Duplicates',
  unaddressed: 'Unaddressed',
  policy_conflict: 'Policy Conflict',
};

interface Props {
  data: GraphData;
  onNodeClick?: (id: string) => void;
}

export default function GraphViewer({ data, onNodeClick }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; label: string; type: string; doc_id?: string } | null>(null);
  const [edgeTooltip, setEdgeTooltip] = useState<{ x: number; y: number; type: string; explanation?: string; confidence: number } | null>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || data.nodes.length === 0) return;
    if (data.nodes.length > 100) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = 500;

    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const defs = svg.append('defs');

    // Animated gradient for links
    const animGrad = defs.append('linearGradient')
      .attr('id', 'link-flow')
      .attr('gradientUnits', 'userSpaceOnUse');
    animGrad.append('stop').attr('offset', '0%').attr('stop-color', 'rgba(59,130,246,0.3)');
    animGrad.append('stop').attr('offset', '50%').attr('stop-color', 'rgba(139,92,246,0.6)');
    animGrad.append('stop').attr('offset', '100%').attr('stop-color', 'rgba(59,130,246,0.3)');

    // Node gradients — richer
    Object.entries(NODE_COLORS).forEach(([type, color]) => {
      const gradient = defs.append('radialGradient')
        .attr('id', `grad-${type}`)
        .attr('cx', '35%').attr('cy', '35%').attr('r', '65%');
      gradient.append('stop').attr('offset', '0%').attr('stop-color', '#ffffff').attr('stop-opacity', 0.9);
      gradient.append('stop').attr('offset', '60%').attr('stop-color', color).attr('stop-opacity', 0.8);
      gradient.append('stop').attr('offset', '100%').attr('stop-color', color).attr('stop-opacity', 1);
    });

    // Glow filters per node type
    Object.entries(NODE_COLORS).forEach(([type, color]) => {
      const f = defs.append('filter').attr('id', `glow-${type}`).attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
      f.append('feGaussianBlur').attr('stdDeviation', '5').attr('result', 'blur');
      f.append('feFlood').attr('flood-color', color).attr('flood-opacity', '0.4').attr('result', 'color');
      f.append('feComposite').attr('in', 'color').attr('in2', 'blur').attr('operator', 'in').attr('result', 'glow');
      const merge = f.append('feMerge');
      merge.append('feMergeNode').attr('in', 'glow');
      merge.append('feMergeNode').attr('in', 'SourceGraphic');
    });

    // Arrow markers
    Object.entries(EDGE_COLORS).forEach(([type, color]) => {
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 26).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color).attr('opacity', 0.9);
    });

    const g = svg.append('g');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);

    // Simulation with more spacing
    const simulation = d3.forceSimulation(data.nodes as d3.SimulationNodeDatum[])
      .force('link', d3.forceLink(data.edges).id((d: any) => d.id).distance(200))
      .force('charge', d3.forceManyBody().strength(-700).distanceMax(600))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(55).iterations(3))
      .force('x', d3.forceX(width / 2).strength(0.05))
      .force('y', d3.forceY(height / 2).strength(0.05));

    // Links
    const link = g.append('g')
      .selectAll('path')
      .data(data.edges)
      .join('path')
      .attr('fill', 'none')
      .attr('stroke', d => EDGE_COLORS[d.edge_type] || '#64748b')
      .attr('stroke-width', d => Math.max(2, d.confidence * 5))
      .attr('stroke-opacity', 0.5)
      .attr('stroke-dasharray', d => d.edge_type === 'supports' ? '8,4' : 'none')
      .attr('marker-end', d => `url(#arrow-${d.edge_type})`)
      .style('cursor', 'pointer')
      .on('mouseover', (event: any, d: any) => {
        d3.select(event.currentTarget as SVGPathElement)
          .attr('stroke-opacity', 1)
          .attr('stroke-width', Math.max(3, d.confidence * 6));
        setEdgeTooltip({ x: event.pageX, y: event.pageY, type: d.edge_type, explanation: d.explanation, confidence: d.confidence });
      })
      .on('mouseout', (event: any, d: any) => {
        d3.select(event.currentTarget as SVGPathElement)
          .attr('stroke-opacity', 0.5)
          .attr('stroke-width', Math.max(2, d.confidence * 5));
        setEdgeTooltip(null);
      });

    // Edge labels with background plates
    const edgeLabels = g.append('g').selectAll('g.edge-label')
      .data(data.edges)
      .join('g')
      .attr('class', 'edge-label');

    edgeLabels.append('rect')
      .attr('fill', 'rgba(5, 11, 20, 0.9)')
      .attr('rx', 4).attr('ry', 4)
      .attr('height', 18)
      .attr('y', -13)
      .attr('x', d => -(EDGE_LABELS[d.edge_type]?.length ?? d.edge_type.length) * 3.2 - 6)
      .attr('width', d => (EDGE_LABELS[d.edge_type]?.length ?? d.edge_type.length) * 6.4 + 12)
      .attr('stroke', d => EDGE_COLORS[d.edge_type] || '#64748b')
      .attr('stroke-width', 0.5)
      .attr('stroke-opacity', 0.4);

    edgeLabels.append('text')
      .text(d => EDGE_LABELS[d.edge_type] ?? d.edge_type)
      .attr('font-size', '8px')
      .attr('fill', d => EDGE_COLORS[d.edge_type] || '#f0f4fc')
      .attr('text-anchor', 'middle')
      .attr('font-weight', 700)
      .attr('letter-spacing', '0.04em');

    // Nodes
    const node = g.append('g')
      .selectAll('g')
      .data(data.nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag<SVGGElement, any>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        }) as any);

    // Outer ring (decorative)
    node.append('circle')
      .attr('r', 24)
      .attr('fill', 'none')
      .attr('stroke', d => NODE_COLORS[d.node_type] || '#06b6d4')
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.3)
      .attr('stroke-dasharray', '4,4');

    // Main node circle
    node.append('circle')
      .attr('r', 20)
      .attr('fill', d => `url(#grad-${d.node_type})`)
      .attr('stroke', d => NODE_COLORS[d.node_type] || '#06b6d4')
      .attr('stroke-width', 2)
      .attr('filter', d => `url(#glow-${d.node_type})`)
      .on('mouseover', (event: any, d: any) => {
        d3.select(event.currentTarget as SVGCircleElement).transition().duration(150).attr('r', 24).attr('stroke-width', 3);
        const outerRing = (event.currentTarget as SVGCircleElement).previousSibling as SVGCircleElement | null;
        if (outerRing) d3.select(outerRing).transition().duration(150).attr('r', 30).attr('stroke-opacity', 0.6);
        setTooltip({ x: event.pageX, y: event.pageY, label: d.label, type: d.node_type, doc_id: d.doc_id });
      })
      .on('mouseout', (event: any) => {
        d3.select(event.currentTarget as SVGCircleElement).transition().duration(150).attr('r', 20).attr('stroke-width', 2);
        const outerRing = (event.currentTarget as SVGCircleElement).previousSibling as SVGCircleElement | null;
        if (outerRing) d3.select(outerRing).transition().duration(150).attr('r', 24).attr('stroke-opacity', 0.3);
        setTooltip(null);
      })
      .on('click', (_event: any, d: any) => { onNodeClick?.(d.id); });

    // Node labels
    node.append('text')
      .text(d => d.label.length > 18 ? d.label.slice(0, 18) + '…' : d.label)
      .attr('font-size', '8px')
      .attr('fill', 'var(--text-secondary)')
      .attr('text-anchor', 'middle')
      .attr('dy', 36)
      .attr('pointer-events', 'none')
      .attr('font-weight', 500);

    // Node icon
    node.append('text')
      .text(d => d.node_type === 'obligation' ? '📑' : '📏')
      .attr('font-size', '16px')
      .attr('text-anchor', 'middle')
      .attr('dy', 6)
      .attr('pointer-events', 'none');

    simulation.on('tick', () => {
      link.attr('d', (d: any) => {
        const dx = d.target.x - d.source.x;
        const dy = d.target.y - d.source.y;
        const dr = Math.sqrt(dx * dx + dy * dy) * 1.5;
        return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
      });
      edgeLabels.attr('transform', (d: any) => {
        const dx = d.target.x - d.source.x;
        const dy = d.target.y - d.source.y;
        const dr = Math.sqrt(dx * dx + dy * dy) * 1.5;
        const x = d.source.x + dx / 2 - (dy / dr) * 20;
        const y = d.source.y + dy / 2 + (dx / dr) * 20;
        return `translate(${x}, ${y})`;
      });
      node.attr('transform', (d: any) => `translate(${d.x}, ${d.y})`);
    });

    return () => { simulation.stop(); };
  }, [data, onNodeClick]);

  if (data.nodes.length > 100) {
    return (
      <div className="empty-state" style={{ height: '500px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div className="empty-icon">⚠️</div>
        <p>Graph is too dense to render ({data.nodes.length} nodes).</p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Please filter your view to reduce node count.</p>
      </div>
    );
  }

  return (
    <div className="graph-container" ref={containerRef} style={{ position: 'relative' }}>
      <svg ref={svgRef} />

      {/* Node Tooltip */}
      {tooltip && (
        <div className="graph-tooltip" style={{ left: tooltip.x + 15, top: tooltip.y + 15 }}>
          <div className="graph-tooltip-type" style={{ color: NODE_COLORS[tooltip.type] }}>
            {tooltip.type}
          </div>
          <div className="graph-tooltip-label">{tooltip.label}</div>
        </div>
      )}

      {/* Edge Tooltip */}
      {edgeTooltip && (
        <div className="graph-tooltip" style={{ left: edgeTooltip.x + 15, top: edgeTooltip.y + 15 }}>
          <div className="graph-tooltip-type" style={{ color: EDGE_COLORS[edgeTooltip.type] }}>
            {EDGE_LABELS[edgeTooltip.type] ?? edgeTooltip.type}
          </div>
          {edgeTooltip.explanation && (
            <div className="graph-tooltip-label">{edgeTooltip.explanation}</div>
          )}
          <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: 4 }}>
            Confidence: {(edgeTooltip.confidence * 100).toFixed(0)}%
          </div>
        </div>
      )}

      <div className="graph-legend">
        <div className="graph-legend-item">
          <div className="graph-legend-dot" style={{ background: NODE_COLORS.obligation, boxShadow: `0 0 8px ${NODE_COLORS.obligation}` }} />
          Obligation
        </div>
        <div className="graph-legend-item">
          <div className="graph-legend-dot" style={{ background: NODE_COLORS.requirement, boxShadow: `0 0 8px ${NODE_COLORS.requirement}` }} />
          Requirement
        </div>
        {Object.entries(EDGE_COLORS).map(([type, color]) => (
          <div key={type} className="graph-legend-item">
            <div className="graph-legend-line" style={{ background: color }} />
            {EDGE_LABELS[type] ?? type}
          </div>
        ))}
      </div>
    </div>
  );
}
