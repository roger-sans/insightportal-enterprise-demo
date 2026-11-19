import { useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowRight, Check, ChevronRight, ClipboardList, Plus, Star, Users } from 'lucide-react';
import type { Adoption, BacklogItem, Catalog, DomainId } from './api';
import { post } from './api';
import { DomainMark, ReadState, useRead } from './portal';

const states = {
  submitted: 'Submitted', triaged: 'Triaged', accepted: 'Accepted', released: 'Released', declined: 'Declined',
};
const kinds = { enhancement: 'Enhancement', 'data-contract': 'Data contract', quality: 'Data quality' };
const actions = { submit: 'Submitted', triage: 'Triaged', accept: 'Accepted', decline: 'Declined', release: 'Released' };
const formatTime = (stamp: string) => new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC',
}).format(new Date(stamp)) + ' UTC';

export function RequestsPage({ catalog }: { catalog: Catalog }) {
  const { data, error, retry } = useRead<BacklogItem[]>('/requests');
  const [filter, setFilter] = useState('');
  const [state, setState] = useState('');
  const [selected, setSelected] = useState<number>();
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState('');
  const entries = data?.filter(row => (!filter || row.domain === filter) && (!state || row.state === state)) ?? [];
  const active = entries.find(row => row.id === selected) ?? entries[0];
  return <>
    <div className="page-title"><div><h1>Product requests</h1><p>Capture cross-domain needs, rank them by value and record acceptance decisions.</p></div>
      <button className="button primary" onClick={() => { setCreating(!creating); setNotice(''); }}>
        {creating ? 'Close form' : <><Plus size={17}/> New request</>}
      </button></div>
    <p className="subtle workflow-note">Reviewer selections simulate roles in this workspace. Use fictional details only.</p>
    {notice && <div className="success-message" role="status"><Check size={17}/>{notice}</div>}
    {creating && <RequestForm catalog={catalog} saved={row => {
      setCreating(false); setFilter(''); setState(''); setSelected(row.id); retry();
      setNotice(`Request IP-${row.id} submitted.`);
    }}/>}
    <div className="control-row">
      <label>Domain <select value={filter} onChange={event => setFilter(event.target.value)}>
        <option value="">All domains</option>{catalog.contract.domains.map(domain =>
          <option key={domain.id} value={domain.id}>{domain.name}</option>)}</select></label>
      <label>State <select value={state} onChange={event => setState(event.target.value)}>
        <option value="">All states</option>{Object.entries(states).map(([id, label]) =>
          <option key={id} value={id}>{label}</option>)}</select></label>
    </div>
    {!data ? <ReadState error={error} retry={retry}/> : <>
      <div className="request-grid">
        <section className="panel request-list"><div className="panel-header"><div><h2>Prioritised intake</h2><p>Score = 3 × impact + 2 × urgency − effort</p></div><ClipboardList size={19}/></div>
          {!entries.length && <p className="empty">No requests match these filters.</p>}
          {entries.map(row => <button key={row.id} onClick={() => { setSelected(row.id); setNotice(''); }}
            className={row.id === active?.id ? 'request-row selected' : 'request-row'} aria-pressed={row.id === active?.id}>
            <DomainMark id={row.domain}/><span><small>IP-{row.id} · {states[row.state]}</small><strong>{row.title}</strong></span>
            <span className="priority" title="Priority score">{row.score}</span><ChevronRight size={15}/>
          </button>)}
        </section>
        {active && <RequestDetail key={`${active.id}:${active.version}`} row={active} catalog={catalog} changed={row => {
          setNotice(`IP-${row.id} is now ${states[row.state].toLowerCase()}.`);
          setState(''); retry();
        }} refresh={retry}/>}
      </div>
    </>}
  </>;
}

function RequestForm({ catalog, saved }: { catalog: Catalog; saved: (row: BacklogItem) => void }) {
  const [domain, setDomain] = useState<DomainId>('finance');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError('');
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      saved(await post<BacklogItem>('/requests', { ...values, impact: Number(values.impact),
        urgency: Number(values.urgency), effort: Number(values.effort) }));
    } catch (failure) {
      setError((failure as Error).message);
      setBusy(false);
    }
  }
  return <form className="panel form-panel" onSubmit={submit}>
    <h2>New analytics request</h2>
    <div className="form-grid">
      <label>Request title<input name="title" required minLength={8} maxLength={96}/></label>
      <label>Domain<select name="domain" value={domain} onChange={event => setDomain(event.target.value as DomainId)}>
        {catalog.contract.domains.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
      <label>Simulated requester<select key={domain} name="requester"><option value="analyst">{catalog.actors.analyst}</option>
        <option value={domain + '-steward'}>{catalog.actors[domain + '-steward']}</option></select></label>
      <label>Type<select name="kind">{Object.entries(kinds).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label>
      <label className="full">Business outcome and acceptance evidence<textarea name="rationale" required minLength={12} maxLength={600} rows={3}/></label>
      <div className="score-inputs full">{['impact', 'urgency', 'effort'].map(key => <label key={key}>
        {key[0].toUpperCase() + key.slice(1)}<input name={key} type="number" min="1" max="5" required defaultValue="3"/></label>)}</div>
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="button primary" disabled={busy} type="submit">{busy ? 'Submitting…' : 'Submit request'}<ArrowRight size={15}/></button>
  </form>;
}

function RequestDetail({ row, catalog, changed, refresh }: {
  row: BacklogItem; catalog: Catalog; changed: (row: BacklogItem) => void; refresh: () => void;
}) {
  const step: Partial<Record<BacklogItem['state'], readonly (keyof typeof actions)[]>> = {
    submitted: ['triage'], triaged: ['accept', 'decline'], accepted: ['release'],
  };
  const rule = { submitted: 'product-owner', triaged: row.requester === row.domain + '-steward' ? 'governance' : row.domain + '-steward',
    accepted: 'release-manager' } as Record<string, string>;
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function decide(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      changed(await post<BacklogItem>(`/requests/${row.id}/decisions`, { ...values, version: row.version }));
    } catch (failure) {
      setError((failure as Error).message);
      setBusy(false);
    }
  }
  return <article className="panel request-detail">
    <div className="catalog-top"><DomainMark id={row.domain}/><span>IP-{row.id} · {kinds[row.kind]}</span>
      <span className={'pill ' + (row.state === 'released' ? 'current' : 'neutral')}><i/>{states[row.state]}</span></div>
    <h2>{row.title}</h2><p>{row.rationale}</p>
    <dl className="request-scores"><div><dt>Impact</dt><dd>{row.impact}/5</dd></div><div><dt>Urgency</dt><dd>{row.urgency}/5</dd></div>
      <div><dt>Effort</dt><dd>{row.effort}/5</dd></div><div><dt>Priority</dt><dd>{row.score}</dd></div></dl>
    <h3>Decision history</h3>
    <ol className="timeline">{row.history.map(event => <li key={event.id}>
      <span className="timeline-marker"/><div><strong>{actions[event.action as keyof typeof actions]}</strong>
        <small>{catalog.actors[event.actor]} · {formatTime(event.recorded_at)}</small><p>{event.note}</p></div>
    </li>)}</ol>
    {step[row.state] && <form onSubmit={decide} className="decision-form">
      <h3>Record decision</h3>
      <p>Assigned reviewer · {catalog.actors[rule[row.state]]}</p>
      <div className="form-grid">
        <label>Simulated reviewer<select name="actor" required defaultValue={rule[row.state]}>
          {Object.entries(catalog.actors).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label>
        <label>Decision<select name="action">{step[row.state]?.map(action =>
          <option value={action} key={action}>{action[0].toUpperCase() + action.slice(1)}</option>)}</select></label>
        <label className="full">Decision rationale<textarea name="note" rows={2} required minLength={12} maxLength={400}/></label>
      </div>
      {error && <p className="form-error" role="alert">{error} <button type="button" className="text-link" onClick={refresh}>Reload requests</button></p>}
      <button className="button primary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save decision'}</button>
    </form>}
  </article>;
}
const rate = (n: number, denominator: number) => Math.round(n / denominator * 100) + '%';

export function AdoptionPage({ catalog }: { catalog: Catalog }) {
  const { data, error, retry } = useRead<Adoption[]>('/adoption');
  const [feedback, setFeedback] = useState<Adoption>();
  return <>
    <div className="page-title"><div><h1>Product adoption</h1><p>Review usage and satisfaction by domain for the simulated September rollout.</p></div></div>
    <div className="inline-note"><Users size={17}/> Synthetic cohorts overlap across domains. Feedback submitted below is stored locally for this demo.</div>
    {!data ? <ReadState error={error} retry={retry}/> :
      <div className="catalog-grid adoption-grid">{data.map(original => {
        const item = original.id === feedback?.id ? feedback : original;
        const domain = catalog.contract.domains.find(candidate => candidate.id === item.id)!;
        return <article key={domain.id} className="panel catalog-card adoption-card">
          <div className="catalog-top"><DomainMark id={domain.id}/><span>{domain.name}</span><a className="text-link" href={'#product/' + domain.id}>Open product <ArrowRight size={14}/></a></div>
          <h2>{domain.product}</h2>
          <div className="adoption-stats">
            <div><small>Latest week active</small><strong>{rate(item.active, item.eligible)}</strong><small>{item.active} / {item.eligible} eligible</small></div>
            <div><small>Repeat use</small><strong>{rate(item.returning, item.active)}</strong><small>{item.returning} of active</small></div>
            <div><small>Satisfaction</small><strong>{item.survey_average.toFixed(1)}<small> / 5</small></strong><small>{item.survey_count} simulated ratings</small></div>
          </div>
          <div className="active-trend"><strong>Weekly active users</strong>{item.weeks.map((count, i) =>
            <div className="active-week" key={i}><span>W{i + 1}</span><div className="bar-track"><span style={{ width: rate(count, item.eligible) }}/></div><b>{count}</b></div>)}</div>
          <FeedbackForm catalog={catalog} item={item} saved={updated => { setFeedback(updated); retry(); }}/>
        </article>;
      })}</div>}
  </>;
}
function FeedbackForm({ catalog, item, saved }: { catalog: Catalog; item: Adoption; saved: (row: Adoption) => void }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      saved(await post<Adoption>('/adoption/feedback', { domain: item.id, actor: values.actor, rating: Number(values.rating) }));
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return <form className="feedback-form" onSubmit={send} aria-label={item.id + ' demo feedback'}>
    <p><Star size={16}/> <strong>Local demo feedback</strong> <span>{item.local_feedback.count
      ? `${item.local_feedback.average?.toFixed(1)}/5 · ${item.local_feedback.count} submitted` : 'No feedback yet'}</span></p>
    <div className="feedback-fields">
      <label>Simulated respondent<select name="actor"><option value="analyst">{catalog.actors.analyst}</option>
        <option value={item.id + '-steward'}>{catalog.actors[item.id + '-steward']}</option></select></label>
      <label>Rating<select name="rating" defaultValue="4">{[1, 2, 3, 4, 5].map(rating =>
        <option value={rating} key={rating}>{rating}</option>)}</select></label>
      <button className="button" disabled={busy} type="submit">{busy ? 'Saving…' : 'Save rating'}</button>
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
  </form>;
}
