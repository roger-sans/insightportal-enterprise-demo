import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import {
  Activity, ArrowDown, ArrowLeft, ArrowRight, ArrowUp, ArrowUpRight,
  BarChart3, BookOpen, CalendarDays, ChevronDown, ChevronRight, CircleCheck, Database,
  ExternalLink, Gauge, LayoutGrid, ListChecks, MapPin, Menu, Radio, ShieldCheck,
  TrendingUp, TriangleAlert, Users, Wallet, Wrench, X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { api } from './api';
import type { Catalog, Dashboard, Domain, DomainId, Metric, MetricResult, Quality } from './api';
import { AdoptionPage, RequestsPage } from './workflows';

const marks: Record<DomainId, { icon: LucideIcon; tone: string }> = {
  finance: { icon: Wallet, tone: 'indigo' }, commercial: { icon: TrendingUp, tone: 'blue' },
  operations: { icon: Wrench, tone: 'orange' }, people: { icon: Users, tone: 'teal' },
};
const pageNames: Record<string, string> = {
  overview: 'Executive overview', catalog: 'Product catalog', metrics: 'Metric dictionary',
  health: 'Data health', requests: 'Requests', adoption: 'Adoption',
};
const groups = [
  { label: 'WORKSPACE', links: [
    ['overview', LayoutGrid], ['catalog', BarChart3], ['metrics', BookOpen],
  ] },
  { label: 'GOVERNANCE', links: [
    ['health', ShieldCheck], ['requests', ListChecks], ['adoption', Activity],
  ] },
] as const;
const checkNames: Record<string, string> = {
  unique_grain: 'Key uniqueness', valid_dimensions: 'Conformed dimensions',
  full_coverage: 'Month and region coverage', metric_invariants: 'Metric rules',
  publication_contract: 'Publication manifest',
};
const monthName = (key: string, long = false) =>
  new Intl.DateTimeFormat('en', { month: long ? 'long' : 'short', timeZone: 'UTC' })
    .format(new Date(key + '-01T00:00:00Z'));
const monthOptions = (year: string, limit: number) =>
  Array.from({ length: limit }, (_, i) => `${year}-${String(i + 1).padStart(2, '0')}`);
const currency = new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });

function format(n: number | null, unit: Metric['unit'], compact = false) {
  if (n === null) return '—';
  if (unit === '%') return `${n.toFixed(1)}%`;
  if (unit === 'EUR' && !compact) return currency.format(n);
  const value = new Intl.NumberFormat('en', {
    notation: compact ? 'compact' : 'standard', maximumFractionDigits: compact ? 2 : 0,
  }).format(n);
  return unit === 'EUR' ? '€' + value : value;
}
function marketingRange(start: string, end: string) {
  const left = monthName(start);
  return start === end ? `${left} ${end.slice(0, 4)}` : `${left} – ${monthName(end)} ${end.slice(0, 4)}`;
}
function useHash() {
  const current = () => window.location.hash.slice(1) || 'overview';
  const [hash, setHash] = useState(current);
  useEffect(() => {
    function update() {
      setHash(current());
      window.scrollTo(0, 0);
    }
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  return hash.split('/');
}
export function useRead<T>(path: string) {
  const [record, setRecord] = useState<{ path: string; data?: T; error?: string }>({ path: '' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api<T>(path, { signal: controller.signal })
      .then(data => setRecord({ path, data }))
      .catch(error => { if (!controller.signal.aborted) setRecord({ path, error: error.message }); });
    return () => controller.abort();
  }, [path, attempt]);
  return {
    data: record.path === path ? record.data : undefined,
    error: record.path === path ? record.error : undefined,
    retry: () => { setRecord({ path: '' }); setAttempt(previous => previous + 1); },
  };
}
export function ReadState({ error, retry }: { error?: string; retry?: () => void }) {
  return <div className="panel read-state" role={error ? 'alert' : 'status'}>
    {error ? <><TriangleAlert size={19}/><p>{error}</p><button className="button" onClick={retry}>Retry</button></>
      : <><Radio size={19}/><p>Loading workspace…</p></>}
  </div>;
}
function Sidebar({ active, open, close }: { active: string; open: boolean; close: () => void }) {
  return <aside className={`sidebar ${open ? 'sidebar-open' : ''}`} aria-label="Workspace navigation">
    <a className="brand" href="#overview" onClick={close}>
      <span className="brand-mark"><BarChart3 size={23} strokeWidth={2.4}/></span>
      <span><strong>InsightPortal</strong><small>ANALYTICS WORKSPACE</small></span>
    </a>
    <button className="icon-button close-nav" onClick={close} aria-label="Close navigation"><X size={21}/></button>
    <nav>{groups.map(group => <div className="nav-group" key={group.label}>
      <p>{group.label}</p>
      {group.links.map(([id, Icon]) => {
        const selected = id === active || (id === 'catalog' && active === 'product');
        return <a key={id} className={selected ? 'active' : ''} aria-current={selected ? 'page' : undefined}
          href={'#' + id} onClick={close}><Icon size={18}/><span>{pageNames[id]}</span></a>;
      })}
    </div>)}</nav>
    <div className="sidebar-bottom">
      <a href="/docs" target="_blank" rel="noreferrer"><span><Database size={17}/> API reference</span><ExternalLink size={14}/></a>
      <div className="environment"><span className="environment-dot"/><div><strong>Synthetic workspace</strong><small>Independent portfolio demo</small></div></div>
    </div>
  </aside>;
}
function Heading({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="page-title"><div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
export function DomainMark({ id, size = 17 }: { id: DomainId; size?: number }) {
  const { icon: Icon, tone } = marks[id];
  return <span className={`domain-mark ${tone}`}><Icon size={size}/></span>;
}
function Status({ status }: { status: Quality['status'] }) {
  const labels = { current: 'Current', late: 'Late publication', blocked: 'Quality blocked' };
  return <span className={`pill ${status}`}><i/>{labels[status]}</span>;
}
function TopBar({ crumb, menu }: { crumb: string; menu: () => void }) {
  return <header className="topbar">
    <div className="breadcrumb">
      <button className="icon-button menu-toggle" aria-label="Open navigation" onClick={menu}><Menu size={21}/></button>
      <span>Enterprise Analytics</span><ChevronRight size={14}/><strong>{crumb}</strong>
    </div>
    <a className="top-status" href="#health"><span/>Demo environment</a>
  </header>;
}
export function App() {
  const [page, subpage] = useHash();
  const catalog = useRead<Catalog>('/catalog');
  const [menu, setMenu] = useState(false);
  const product = catalog.data?.contract.domains.find(domain => domain.id === subpage);
  const crumb = page === 'product' ? product?.name ?? 'Product catalog' : pageNames[page] ?? 'Workspace';
  return <div className="layout">
    <a className="skip-link" href="#main-content" onClick={event => {
      event.preventDefault();
      document.getElementById('main-content')?.focus();
    }}>Skip to content</a>
    <Sidebar active={page} open={menu} close={() => setMenu(false)}/>
    {menu && <button className="scrim" aria-label="Close navigation overlay" onClick={() => setMenu(false)}/>}
    <div className="workspace">
      <TopBar crumb={crumb} menu={() => setMenu(true)}/>
      <main className="content" id="main-content" tabIndex={-1}>
        {!catalog.data ? <ReadState error={catalog.error} retry={catalog.retry}/>
          : page === 'overview' || product ? <Analytics key={product?.id ?? 'overview'} catalog={catalog.data} domain={product}/>
          : page === 'catalog' ? <CatalogPage catalog={catalog.data}/>
          : page === 'metrics' ? <MetricPage catalog={catalog.data} selected={subpage}/>
          : page === 'health' ? <HealthPage catalog={catalog.data}/>
          : page === 'requests' ? <RequestsPage catalog={catalog.data}/>
          : page === 'adoption' ? <AdoptionPage catalog={catalog.data}/>
          : <><Heading title="Page unavailable" description="Choose a page from the workspace navigation."/><a href="#overview">Return to overview</a></>}
      </main>
    </div>
  </div>;
}

type Filters = { year: string; start: string; end: string; site: string };
function DashboardFilters({ catalog, filters, update }: { catalog: Catalog; filters: Filters; update: (value: Filters) => void }) {
  const months = monthOptions(filters.year, catalog.years[filters.year]);
  return <div className="filters"><div className="filter-group">
    <label><CalendarDays size={15}/>
      <select aria-label="Calendar year" value={filters.year} onChange={event => {
        const year = event.target.value;
        const available = monthOptions(year, catalog.years[year]);
        update({ ...filters, year, start: available[0], end: available[available.length - 1] });
      }}>{Object.keys(catalog.years).sort().reverse().map(year => <option key={year}>{year}</option>)}</select>
      <ChevronDown size={13} className="select-chevron"/>
    </label>
    <label><span>From</span><select aria-label="Start month" value={filters.start} onChange={event =>
      update({ ...filters, start: event.target.value })}>{months.filter(key => key <= filters.end).map(key =>
        <option key={key} value={key}>{monthName(key)}</option>)}</select><ChevronDown size={13} className="select-chevron"/></label>
    <label><span>To</span><select aria-label="End month" value={filters.end} onChange={event =>
      update({ ...filters, end: event.target.value })}>{months.filter(key => key >= filters.start).map(key =>
        <option key={key} value={key}>{monthName(key)}</option>)}</select><ChevronDown size={13} className="select-chevron"/></label>
    <label><MapPin size={15}/><select aria-label="Service region" value={filters.site} onChange={event =>
      update({ ...filters, site: event.target.value })}><option value="">All regions</option>{catalog.contract.sites.map(site =>
        <option key={site.id} value={site.id}>{site.name}</option>)}</select><ChevronDown size={13} className="select-chevron"/></label>
  </div></div>;
}

function Analytics({ catalog, domain }: { catalog: Catalog; domain?: Domain }) {
  const domains = domain ? [domain] : catalog.contract.domains;
  const cards = domains.flatMap(group => (domain ? group.metrics : group.metrics.slice(0, 1)).map(metric => ({ group, metric })));
  const choices = domains.flatMap(group => group.metrics);
  const [filters, setFilters] = useState<Filters>({ year: '2026', start: '2026-01', end: '2026-09', site: '' });
  const [chosen, setChosen] = useState(choices[0].id);
  const [drill, setDrill] = useState<string | null>(null);
  const query = new URLSearchParams({ start: filters.start, end: filters.end });
  if (domain) query.set('domain', domain.id);
  if (filters.site) query.set('site', filters.site);
  [...new Set([...cards.map(card => card.metric.id), chosen])].forEach(id => query.append('metrics', id));
  const { data, error, retry } = useRead<Dashboard>('/dashboard?' + query);
  const metric = choices.find(option => option.id === chosen)!;
  const result = data?.metrics.find(row => row.id === chosen);
  const group = domains.find(item => item.metrics.some(option => option.id === chosen))!;
  const alerts = data?.quality.filter(quality => quality.status !== 'current') ?? [];
  const update = (value: Filters) => { setFilters(value); setDrill(null); };
  return <>
    {domain && <a className="back-link" href="#catalog"><ArrowLeft size={14}/> Product catalog</a>}
    <Heading title={domain?.product ?? 'Executive overview'}
      description={domain?.purpose ?? 'Track business performance across four governed analytics products.'}
      action={<a className="button" href={domain ? '#metrics/' + chosen : '#catalog'}>
        {domain ? <BookOpen size={16}/> : <LayoutGrid size={16}/>}
        {domain ? 'KPI definition' : 'Browse products'}<ChevronRight size={15}/>
      </a>}/>
    <DashboardFilters catalog={catalog} filters={filters} update={update}/>
    {!data ? <ReadState error={error} retry={retry}/> : <>
      {alerts.length > 0 && <a className="freshness-banner" href="#health">
        <TriangleAlert size={18}/><span><strong>{alerts.some(alert => alert.status === 'blocked')
          ? 'Some metrics have been withheld' : (alerts.length === 1 ? 'One product is behind its freshness target' : 'Some products are behind their freshness targets')}</strong>
          <span>{alerts.map(alert => domains.find(option => option.id === alert.id)?.name).join(', ')} · Latest validated publication</span></span>
        <span className="banner-link">View data health <ArrowRight size={15}/></span>
      </a>}
      <section className="kpi-grid" aria-label="Key performance indicators">
        {cards.map(({ group: cardGroup, metric: item }) => {
          const outcome = data.metrics.find(row => row.id === item.id);
          return <MetricCard key={item.id} group={cardGroup} metric={item} result={outcome}
            selected={item.id === chosen} select={() => { setChosen(item.id); setDrill(null); }}/>;
        })}
      </section>
      <div className="explore-grid">
        <section className="panel chart-panel">
          <div className="panel-header">
            <div><h2>Performance trend</h2><p>{metric.name} · {marketingRange(filters.start, filters.end)}</p></div>
            <label className="metric-select"><select aria-label="Performance metric" value={chosen} onChange={event => {
              setChosen(event.target.value); setDrill(null);
            }}>{choices.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><ChevronDown size={14}/></label>
          </div>
          {result ? <Trend metric={metric} result={result} month={drill} onMonth={setDrill}/> : <p className="chart-empty">This metric is withheld until its contract passes.</p>}
        </section>
        <section className="panel regions-panel">
          <div className="panel-header"><div><h2>Regional breakdown</h2><p>{drill ? `${monthName(drill, true)} ${drill.slice(0, 4)}` : 'Selected period'}</p></div><MapPin size={17}/></div>
          {drill ? <RegionalDrill catalog={catalog} metric={metric} domain={group}
            month={drill} site={filters.site} clear={() => setDrill(null)} select={site => setFilters({ ...filters, site })}/>
            : <Regions catalog={catalog} metric={metric} rows={result?.sites ?? []}
              site={filters.site} select={site => update({ ...filters, site })}/>}
          <a className="text-link region-definition" href={'#metrics/' + chosen}>View KPI definition <ArrowRight size={15}/></a>
        </section>
      </div>
      <section className="overview-products" aria-label="Products in view">
        <div className="section-title"><h2>{domain ? 'Product governance' : 'Analytics products'}</h2>
          <a className="text-link" href={domain ? '#health' : '#catalog'}>{domain ? 'View data health' : 'Open catalog'} <ArrowRight size={15}/></a>
        </div>
        <div className="compact-grid">
          {domains.map(candidate => <a key={candidate.id} className="panel product-shortcut" href={domain ? '#metrics/' + chosen : '#product/' + candidate.id}>
            <DomainMark id={candidate.id}/><div><strong>{domain ? candidate.owner : candidate.name}</strong><small>{domain ? 'Accountable data owner' : candidate.product}</small></div><ChevronRight size={15}/>
          </a>)}
        </div>
      </section>
    </>}
  </>;
}

function MetricCard({ group, metric, result, selected, select }: {
  group: Domain; metric: Metric; result?: MetricResult; selected: boolean; select: () => void;
}) {
  const good = result?.delta != null && (metric.direction === 'up' ? result.delta >= 0 : result.delta <= 0);
  return <button className={`panel kpi-card ${selected ? 'selected' : ''}`} onClick={select} aria-pressed={selected}>
    <span className="kpi-top"><DomainMark id={group.id}/><small>{group.name}</small><ArrowUpRight className="kpi-arrow" size={16}/></span>
    <span className="kpi-label">{metric.name}</span>
    <strong className="kpi-value">{format(result?.value ?? null, metric.unit, metric.unit === 'EUR')}</strong>
    <span className="kpi-change">
      {result?.delta != null ? <>
        <span className={`change ${good ? 'favorable' : 'unfavorable'}`}>
          {result.delta >= 0 ? <ArrowUp size={12}/> : <ArrowDown size={12}/>}
          {Math.abs(result.delta).toFixed(1)}{metric.unit === '%' ? ' pp' : '%'}</span>
        <small>vs same period last year</small></> : <small>{result ? 'No comparable period' : 'Withheld by quality gate'}</small>}
    </span>
  </button>;
}
function Trend({ metric, result, month, onMonth }: { metric: Metric; result: MetricResult; month: string | null; onMonth: (month: string | null) => void }) {
  const points = result.trend;
  const series = points.flatMap(point => point.value === null ? [] : [point.value]);
  if (!series.length) return <p className="chart-empty">No comparable values for this selection.</p>;
  const w = 636, h = 215, left = 62, right = 598, top = 17, bottom = 173;
  const values = result.trend_goal === null ? series : [...series, result.trend_goal];
  const maximum = Math.max(...values);
  const minimum = Math.min(...values);
  const spread = Math.max(maximum - minimum, maximum * 0.12, 1);
  const rawStep = (spread * 1.25) / 4;
  const base = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const step = ([1, 2, 2.5, 5, 10].find(number => base * number >= rawStep) ?? 10) * base;
  const low = Math.max(0, Math.floor((minimum - spread * 0.10) / step) * step);
  const upper = Math.max(low + step * 4, Math.ceil(maximum / step) * step);
  const ticks = Array.from({ length: Math.round((upper - low) / step) + 1 }, (_, i) => low + step * i);
  const x = (i: number) => points.length === 1 ? (left + right) / 2 : left + (right - left) * i / (points.length - 1);
  const y = (v: number) => bottom - (bottom - top) * (v - low) / (upper - low);
  const coords = points.map((point, i) => point.value === null ? null : [x(i), y(point.value)]);
  const line = coords.reduce((d, coord, i) => coord ? d + `${coords[i - 1] ? ' L' : ' M'} ${coord.join(' ')}` : d, '');
  const shade = coords.every(Boolean) && points.length > 1 ? line +
    ` L ${x(points.length - 1)} ${bottom} L ${left} ${bottom} Z` : undefined;
  return <>
    <svg className="trend" viewBox={`0 0 ${w} ${h}`} role="group" aria-label={`${metric.name} by month. Select a month to drill into its regional breakdown.`}>
      <defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1" gradientUnits="objectBoundingBox">
        <stop offset="0%" stopColor="#6d61ec" stopOpacity=".18"/><stop offset="100%" stopColor="#6d61ec" stopOpacity=".025"/>
      </linearGradient></defs>
      {ticks.map(tick => <g key={tick}>
        <line x1={left} x2={right} y1={y(tick)} y2={y(tick)} className="gridline"/>
        <text x={left - 12} y={y(tick) + 4} textAnchor="end">{format(tick, metric.unit, true)}</text>
      </g>)}
      {shade && <path d={shade} fill="url(#area)"/>}
      {result.trend_goal !== null && <line className="goal-line" x1={left} x2={right} y1={y(result.trend_goal)} y2={y(result.trend_goal)}/>}
      <path d={line} fill="none" stroke="#6454e8" strokeWidth="2.7" strokeLinejoin="round"/>
      {points.map((point, i) => <g key={point.month} className={month === point.month ? 'month-point chosen' : 'month-point'}
        role="button" tabIndex={0} aria-label={`${monthName(point.month, true)}, ${format(point.value, metric.unit)}`}
        aria-pressed={month === point.month} onClick={() => onMonth(month === point.month ? null : point.month)}
        onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault(); onMonth(month === point.month ? null : point.month);
        } }}>
        <title>{`${monthName(point.month, true)} · ${format(point.value, metric.unit)}`}</title>
        <rect x={x(i) - 15} y={top} width="30" height={bottom + 29 - top} fill="transparent"/>
        {point.value !== null && <circle cx={x(i)} cy={y(point.value)} r="4.5"/>}
        <text x={x(i)} y={bottom + 23} textAnchor="middle">{monthName(point.month)}</text>
      </g>)}
    </svg>
    <div className="chart-legend"><span><i className="actual-key"/> Actual</span>
      {result.trend_goal !== null && <span><i className="target-key"/> Target · {format(result.trend_goal, metric.unit)}</span>}
      {month && <button className="text-link" onClick={() => onMonth(null)}>Clear month <X size={13}/></button>}
    </div>
  </>;
}
function Regions({ catalog, metric, rows, site, select }: {
  catalog: Catalog; metric: Metric; rows: MetricResult['sites']; site: string; select: (site: string) => void;
}) {
  const ranked = [...rows].sort((a, b) => {
    if (a.value === null) return b.value === null ? 0 : 1;
    if (b.value === null) return -1;
    return metric.direction === 'up' ? b.value - a.value : a.value - b.value;
  });
  const peak = metric.unit === '%' ? 100 : Math.max(1, ...rows.map(row => row.value ?? 0));
  return rows.length ? <div className="regional-rows">{ranked.map(row =>
    <button className="region-row" key={row.id} onClick={() => select(site === row.id ? '' : row.id)} aria-pressed={site === row.id}
      title={site === row.id ? 'Clear region filter' : 'Filter dashboard to region'}>
      <span className="region-label"><strong>{catalog.contract.sites.find(item => item.id === row.id)?.name}</strong><span>{format(row.value, metric.unit)}</span></span>
      <span className="bar-track"><span style={{ width: `${Math.max(0, (row.value ?? 0) / peak * 100)}%` }}/></span>
    </button>)}</div> : <p className="chart-empty">No regional values available.</p>;
}
function RegionalDrill({ catalog, metric, domain, month, site, clear, select }: {
  catalog: Catalog; metric: Metric; domain: Domain; month: string; site: string; clear: () => void; select: (site: string) => void;
}) {
  const query = new URLSearchParams({ start: month, end: month, domain: domain.id, metrics: metric.id });
  if (site) query.set('site', site);
  const { data, error, retry } = useRead<Dashboard>('/dashboard?' + query);
  return <>{data ? <Regions catalog={catalog} metric={metric} rows={data.metrics[0]?.sites ?? []} site={site} select={select}/>
    : <ReadState error={error} retry={retry}/>}<button className="text-link drill-back" onClick={clear}><ArrowLeft size={14}/> Show selected period</button></>;
}

function CatalogPage({ catalog }: { catalog: Catalog }) {
  const { data, error, retry } = useRead<Dashboard>('/dashboard?metrics=revenue');
  return <>
    <Heading title="Product catalog" description="Discover the analytics products, their intended consumers and accountable owners."/>
    {error && <ReadState error={error} retry={retry}/>}
    <div className="catalog-grid">{catalog.contract.domains.map(domain => {
      const status = data?.quality.find(outcome => outcome.id === domain.id)?.status;
      return <article className="panel catalog-card" key={domain.id}>
        <div className="catalog-top"><DomainMark id={domain.id} size={20}/><span>{domain.name}</span>{status && <Status status={status}/>}</div>
        <h2>{domain.product}</h2><p>{domain.purpose}</p>
        <dl className="details"><div><dt>Data owner</dt><dd>{domain.owner}</dd></div><div><dt>Consumers</dt><dd>{domain.consumer}</dd></div>
          <div><dt>Certified KPIs</dt><dd>{domain.metrics.length} · v{catalog.contract.version}</dd></div></dl>
        <a className="button primary" href={'#product/' + domain.id}>Open dashboard <ArrowRight size={15}/></a>
      </article>;
    })}</div>
  </>;
}

function MetricPage({ catalog, selected }: { catalog: Catalog; selected: string }) {
  const [search, setSearch] = useState('');
  const [domain, setDomain] = useState('');
  const entries = catalog.contract.domains.flatMap(group => group.metrics.map(metric => ({ group, metric })))
    .filter(({ group, metric }) => (selected ? selected === metric.id : (!domain || domain === group.id)) &&
      [metric.name, group.name, metric.definition].join(' ').toLowerCase().includes(selected ? '' : search.toLowerCase()));
  return <>
    {selected && <a href="#metrics" className="back-link"><ArrowLeft size={14}/> Metric dictionary</a>}
    <Heading title={selected && entries.length ? entries[0].metric.name : 'Metric dictionary'}
      description="Definitions, calculation rules, ownership and lineage for the shared semantic model."/>
    {!selected && <div className="control-row">
      <label>Search metrics <input type="search" placeholder="Name, definition or domain" value={search} onChange={event => setSearch(event.target.value)}/></label>
      <label>Domain <select value={domain} onChange={event => setDomain(event.target.value)}><option value="">All domains</option>
        {catalog.contract.domains.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
    </div>}
    {!entries.length && <div className="panel empty">No metrics match this selection.</div>}
    <div className={selected ? 'single-detail' : 'catalog-grid'}>
      {entries.map(({ group, metric }) => <article className="panel catalog-card" key={metric.id}>
        <div className="catalog-top"><DomainMark id={group.id}/><span>{group.name}</span><span className="pill current"><i/>Contract v{catalog.contract.version}</span></div>
        {!selected && <h2><a href={'#metrics/' + metric.id}>{metric.name}</a></h2>}
        <p>{metric.definition}</p><div className="formula">{metric.formula}</div>
        <dl className="details metric-details">
          <div><dt>Accountable owner</dt><dd>{group.owner}</dd></div>
          <div><dt>Exclusions</dt><dd>{metric.exclusions}</dd></div>
          <div><dt>Target</dt><dd>{format(metric.goal, metric.unit)} {metric.goal_basis === 'monthly_global' ? 'per month · all regions' : 'for the selected period'}</dd></div>
          <div><dt>Serving grain</dt><dd>Calendar month × service region</dd></div>
        </dl>
        <div className="lineage" aria-label="Metric lineage">
          <span>{group.source}</span><ChevronRight size={14}/><code>{group.table}</code><ChevronRight size={14}/><span>{metric.name}</span>
        </div>
        <a href={'#product/' + group.id} className="text-link">Open product <ArrowRight size={15}/></a>
      </article>)}
    </div>
  </>;
}

function HealthPage({ catalog }: { catalog: Catalog }) {
  const { data, error, retry } = useRead<Dashboard>('/dashboard?metrics=revenue');
  const current = data?.quality.filter(item => item.status === 'current').length ?? 0;
  const passed = data?.quality.reduce((n, item) => n + Object.values(item.checks).filter(Boolean).length, 0);
  const asOf = new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC',
  }).format(new Date(catalog.contract.scenario_as_of));
  return <>
    <Heading title="Data health" description="Inspect the publication SLA, contract checks and availability of each product."
      action={<button className="button" onClick={retry}><Activity size={16}/> Recheck contracts</button>}/>
    {!data ? <ReadState error={error} retry={retry}/> : <>
      <div className="health-summary">
        <div className="panel health-stat"><Gauge size={20}/><strong>{current} / {data.quality.length}</strong><span>Products within SLA</span></div>
        <div className="panel health-stat"><CircleCheck size={20}/><strong>{passed} / {data.quality.reduce((n, item) => n + Object.keys(item.checks).length, 0)}</strong><span>Contract checks passed</span></div>
        <div className="panel health-stat"><Database size={20}/><strong>{data.mode === 'local' ? 'Local SQL' : 'Snowflake'}</strong><span>Active analytics source</span></div>
      </div>
      <p className="subtle">Freshness is measured against the fixed demo clock · {asOf} UTC.</p>
      <div className="catalog-grid">{data.quality.map(item => {
        const domain = catalog.contract.domains.find(group => group.id === item.id)!;
        return <article className="panel catalog-card health-card" key={item.id}>
          <div className="catalog-top"><DomainMark id={domain.id}/><span>{domain.name}</span><Status status={item.status}/></div>
          <h2>{domain.product}</h2>
          <dl className="details"><div><dt>Publication age</dt><dd>{item.age_hours === null ? 'Unavailable' : `${item.age_hours} h / ${item.sla_hours} h SLA`}</dd></div>
            <div><dt>Coverage through</dt><dd>{item.through_month ?? 'Unavailable'} · {item.rows}/{item.expected_rows} aggregate rows</dd></div></dl>
          <ul className="checks">{Object.entries(item.checks).map(([name, ok]) => <li key={name}>
            {ok ? <CircleCheck size={15}/> : <TriangleAlert size={15}/>} {checkNames[name]} <strong>{ok ? 'Pass' : 'Fail'}</strong>
          </li>)}</ul>
          <a href={'#product/' + item.id} className="text-link">Open product <ArrowRight size={15}/></a>
        </article>;
      })}</div>
    </>}
  </>;
}
