import { useEffect, useMemo, useState } from 'react'
import { api, clearSession, getUser, setSession } from './api.js'

const DEMO_TEXT = 'Your SingPost parcel has been detained. Pay $2.03 today to arrange delivery at http://example-suspicious-link.test'
const REGIONS = ['Singapore-wide', 'Central', 'East', 'North', 'Northeast', 'West']
const CATEGORIES = ['delivery', 'banking', 'government', 'job-task', 'investment', 'phishing', 'marketplace', 'refund', 'tech-support', 'other']
const pretty = value => (value || 'other').replaceAll('-', ' ').replace(/\b\w/g, letter => letter.toUpperCase())
const humanDate = value => value ? new Date(value).toLocaleDateString('en-SG', { day: 'numeric', month: 'short' }) : 'Recently'

function Icon({ name, size = 18 }) {
  const paths = {
    compass: <><circle cx="12" cy="12" r="9"/><path d="m15.8 8.2-2.4 5.2-5.2 2.4 2.4-5.2z"/></>,
    search: <><circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4 4"/></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
    people: <><circle cx="9" cy="8" r="3"/><path d="M3 20v-1a6 6 0 0 1 12 0v1M16 5.5a3 3 0 0 1 0 5.8M18 14a5 5 0 0 1 3 4.6V20"/></>,
    chart: <><path d="M4 19V5m0 14h16M8 15l3-4 3 2 5-7"/><path d="M16 6h3v3"/></>,
    map: <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15m6-12v15"/></>,
    arrow: <><path d="M5 12h14m-6-6 6 6-6 6"/></>,
    close: <><path d="m18 6-12 12M6 6l12 12"/></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
    share: <><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.7 10.7 6.6-4.4m-6.6 7 6.6 4.4"/></>,
    link: <><path d="M10 13a5 5 0 0 0 7.5.5l3-3A5 5 0 0 0 13.5 3l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3A5 5 0 0 0 10.5 21l1.7-1.7"/></>,
    check: <><path d="m5 12 4 4L19 6"/></>,
    upload: <><path d="M12 16V4m-4 4 4-4 4 4M4 16v4h16v-4"/></>,
    plus: <><path d="M12 5v14m-7-7h14"/></>,
    alert: <><path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.shield}</svg>
}

function Brand() { return <a className="brand" href="#top" aria-label="ScamDar home"><span className="brand-mark"><Icon name="compass" size={23} /></span><span>scam<span>dar</span><small>COMMUNITY SCAM RADAR</small></span></a> }
function RiskPill({ level }) { const key = (level || 'low').toLowerCase(); return <span className={`risk-pill risk-${key}`}><i />{level || 'Low'} risk</span> }

function App() {
  const [page, setPage] = useState(() => new URLSearchParams(window.location.search).has('trusted') ? 'trusted' : 'check')
  const [trustedToken] = useState(() => new URLSearchParams(window.location.search).get('trusted') || '')
  const [text, setText] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [apiOnline, setApiOnline] = useState(false)
  const [user, setUser] = useState(getUser)
  const [authOpen, setAuthOpen] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)
  const [trustedOpen, setTrustedOpen] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const [feed, setFeed] = useState([])
  const [selected, setSelected] = useState(null)
  const [comments, setComments] = useState([])
  const [trends, setTrends] = useState(null)
  const [filterCategory, setFilterCategory] = useState('all')
  const [filterRegion, setFilterRegion] = useState('all')
  const [sort, setSort] = useState('newest')
  const [elder, setElder] = useState(false)
  const [toast, setToast] = useState('')
  const [trustedLink, setTrustedLink] = useState('')
  const [notifications, setNotifications] = useState([])
  const [adminSummary, setAdminSummary] = useState(null)
  const [moderationFlags, setModerationFlags] = useState([])
  const [adminUsers, setAdminUsers] = useState([])

  useEffect(() => { api('/api/health').then(() => setApiOnline(true)).catch(() => setApiOnline(false)) }, [])
  useEffect(() => {
    if (page === 'check' || page === 'feed' || page === 'map' || page === 'trends') loadFeed()
    if (page === 'trends' || page === 'map') api('/api/trends').then(setTrends).catch(() => {})
    if (page === 'admin' && user && ['moderator', 'admin'].includes(user.role)) loadAdmin()
  }, [page, filterCategory, filterRegion, sort])
  useEffect(() => { if (user) api('/api/notifications').then(data => setNotifications(data.items || [])).catch(() => {}) }, [user])
  useEffect(() => { if (toast) { const timer = setTimeout(() => setToast(''), 3600); return () => clearTimeout(timer) } }, [toast])

  async function loadFeed() {
    try {
      const params = new URLSearchParams({ sort, limit: '40' })
      if (filterCategory !== 'all') params.set('category', filterCategory)
      if (filterRegion !== 'all') params.set('region', filterRegion)
      const data = await api(`/api/reports?${params}`)
      setFeed(data.items || [])
      setApiOnline(true)
    } catch (e) { setError(e.message); setApiOnline(false) }
  }

  async function loadAdmin() {
    try {
      const [summary, flags] = await Promise.all([api('/api/admin/summary'), api('/api/moderation/flags')])
      setAdminSummary(summary); setModerationFlags(flags.items || [])
      if (user?.role === 'admin') setAdminUsers((await api('/api/admin/users')).items || [])
    } catch (e) { setToast(e.message) }
  }

  async function moderateFlag(flag, action) {
    try {
      await api(`/api/moderation/flags/${flag.id}?action=${encodeURIComponent(action)}`, { method: 'PATCH' })
      const labels = { dismiss: 'dismissed', hide: 'hidden', verify: 'verified', lock: 'locked' }
      setToast(`Flag ${labels[action] || 'updated'}.`)
      await loadAdmin()
    } catch (e) { setToast(e.message) }
  }

  async function mergeFlaggedReport(sourceId) {
    const destination = Number(window.prompt('Enter the report ID to merge this into:'))
    if (!Number.isInteger(destination) || destination < 1) return
    try { await api(`/api/moderation/reports/${sourceId}/merge?into_id=${destination}`, { method: 'POST' }); setToast(`Report #${sourceId} was merged into #${destination}.`); await loadAdmin() }
    catch (e) { setToast(e.message) }
  }

  async function warnUser(userId) {
    const message = window.prompt('Write a short moderation warning:')
    if (!message) return
    try { await api(`/api/moderation/users/${userId}/warn`, { method: 'POST', body: JSON.stringify({ message }) }); setToast('Moderation warning sent and recorded.'); await loadAdmin() }
    catch (e) { setToast(e.message) }
  }

  async function setRole(userId, role) {
    try { await api(`/api/admin/users/${userId}/role?role=${encodeURIComponent(role)}`, { method: 'PATCH' }); await loadAdmin(); setToast('Account role updated and recorded.') }
    catch (e) { setToast(e.message) }
  }

  async function helpfulComment(commentId) {
    if (!user) { setAuthOpen(true); return }
    try {
      const result = await api(`/api/comments/${commentId}/helpful`, { method: 'POST' })
      setComments(items => items.map(item => item.id === commentId ? { ...item, helpful_count: result.helpful_count } : item))
    } catch (e) { setToast(e.message) }
  }

  async function runCheck(event) {
    event?.preventDefault()
    if (text.trim().length < 3) { setError('Paste a message, URL, phone number or email to check.'); return }
    setLoading(true); setError(''); setAnalysis(null)
    try { setAnalysis(await api('/api/analyze', { method: 'POST', body: JSON.stringify({ text }) })) }
    catch (e) { setError(e.message) } finally { setLoading(false) }
  }

  async function inspectReport(report) {
    try {
      const detail = await api(`/api/reports/${report.id}`)
      setSelected(detail)
      setComments((await api(`/api/reports/${report.id}/comments`)).items || [])
    } catch (e) { setToast(e.message) }
  }

  async function authSubmit(event) {
    event.preventDefault(); setError('')
    const form = new FormData(event.currentTarget)
    const body = { email: form.get('email'), password: form.get('password') }
    if (authMode === 'signup') body.display_name = form.get('display_name')
    try {
      const data = await api(`/api/auth/${authMode === 'signup' ? 'signup' : 'login'}`, { method: 'POST', body: JSON.stringify(body) })
      setSession(data.token, data.user); setUser(data.user); setAuthOpen(false); setToast(`Welcome, ${data.user.display_name || 'back'}!`)
    } catch (e) { setError(e.message) }
  }

  function logout() { api('/api/auth/logout', { method: 'POST' }).catch(() => {}); clearSession(); setUser(null); setToast('You have signed out.') }

  async function sendVote(reportId, choice) {
    if (!user) { setAuthOpen(true); return }
    try {
      const voteSummary = await api(`/api/reports/${reportId}/votes`, { method: 'POST', body: JSON.stringify({ choice }) })
      setSelected(current => current?.id === reportId ? { ...current, vote_summary: voteSummary } : current)
      setFeed(items => items.map(item => item.id === reportId ? { ...item, vote_summary: voteSummary } : item))
    } catch (e) { setToast(e.message) }
  }

  async function addComment(event) {
    event.preventDefault()
    if (!user) { setAuthOpen(true); return }
    const form = new FormData(event.currentTarget)
    try {
      const comment = await api(`/api/reports/${selected.id}/comments`, { method: 'POST', body: JSON.stringify({ body: form.get('body'), parent_id: form.get('parent_id') ? Number(form.get('parent_id')) : null }) })
      setComments(items => [...items, comment]); event.currentTarget.reset(); setToast('Your comment was added.')
    } catch (e) { setToast(e.message) }
  }

  async function createReport(event) {
    event.preventDefault()
    if (!user) { setReportOpen(false); setAuthOpen(true); return }
    const form = new FormData(event.currentTarget)
    const body = Object.fromEntries(form.entries())
    try {
      let result
      try { result = await api('/api/reports', { method: 'POST', body: JSON.stringify(body) }) }
      catch (e) {
        if (e.status !== 409 || !e.data?.duplicate) throw e
        const openExisting = window.confirm(`${e.message}\n\nOpen a similar existing report? Choose Cancel to add another report anyway.`)
        if (openExisting && e.data.similar_reports?.[0]) { setReportOpen(false); await inspectReport(e.data.similar_reports[0]); return }
        result = await api('/api/reports?allow_duplicate=true', { method: 'POST', body: JSON.stringify(body) })
      }
      setReportOpen(false); setToast('Report added to the community feed.'); setAnalysis(null); setText(''); setPage('feed'); await loadFeed()
      if (result.id) inspectReport(result)
    } catch (e) { setToast(e.message) }
  }

  async function askContact(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    try {
      const result = await api('/api/trusted-contacts', { method: 'POST', body: JSON.stringify({ contact_email: form.get('email'), message: form.get('message') }) })
      setTrustedLink(`${window.location.origin}/?trusted=${result.response_token}`)
      setToast('Trusted-contact link created. Share it privately; no email is sent in this demo.')
    } catch (e) { setToast(e.message) }
  }

  const categories = useMemo(() => ['all', ...CATEGORIES], [])
  const shareText = analysis ? `⚠️ SCAMDAR COMMUNITY ALERT\n\n${analysis.level.toUpperCase()} RISK — ${analysis.score}/100\n\nWarning signs:\n${analysis.signals.map(s => `• ${s.label}`).join('\n')}\n\n${analysis.recommended_action}\n\nChecked using ScamDar.` : selected ? `⚠️ SCAMDAR COMMUNITY ALERT\n\n${selected.title}\n${selected.risk_level?.toUpperCase()} RISK — ${selected.score}/100\n\n${selected.content}\n\nDo not click suspicious links. Checked using ScamDar.` : ''

  return <div id="top" className={`app-shell ${elder ? 'elder-mode' : ''}`}>
    <div className="top-note"><span className="top-note-dot" /> Community-powered awareness for Singapore <span className="top-note-sep">·</span> Check before you click</div>
    <header className="site-header"><div className="header-inner"><Brand />
      <nav className="main-nav" aria-label="Main navigation">
        <button className={page === 'check' ? 'active' : ''} onClick={() => setPage('check')}>Check a message</button>
        <button className={page === 'feed' ? 'active' : ''} onClick={() => setPage('feed')}>Community feed</button>
        <button className={page === 'trends' ? 'active' : ''} onClick={() => setPage('trends')}>Trends</button>
        <button className={page === 'map' ? 'active' : ''} onClick={() => setPage('map')}>Regional map</button>
        {user && ['moderator', 'admin'].includes(user.role) && <button className={page === 'admin' ? 'active' : ''} onClick={() => setPage('admin')}>Moderation</button>}
      </nav>
      <div className="header-actions"><button className="elder-toggle" onClick={() => setElder(!elder)} aria-pressed={elder}><span className="elder-a">A</span> {elder ? 'Standard view' : 'Easy read'}</button>
        {user ? <div className="user-chip"><button className="notification-button" onClick={() => setToast(notifications.length ? `${notifications.length} notification${notifications.length === 1 ? '' : 's'}: ${notifications[0].message}` : 'You are all caught up.')} aria-label="Notifications"><Icon name="bell" /><b>{notifications.length}</b></button><span className="user-avatar">{user.display_name?.slice(0, 1).toUpperCase()}</span><button className="user-name" onClick={logout}>{user.display_name}<small>Sign out</small></button></div>
          : <button className="sign-in" onClick={() => { setAuthMode('login'); setAuthOpen(true) }}>Sign in <Icon name="arrow" size={16} /></button>}
      </div>
      <button className="mobile-menu" onClick={() => setPage(page === 'check' ? 'feed' : 'check')} aria-label="Toggle navigation"><Icon name="menu" /></button>
    </div></header>

    <main>
      {page === 'check' && <>
        <section className="hero-grid"><div className="hero-copy"><div className="eyebrow"><span>THE COMMUNITY SCAM RADAR</span><span className="eyebrow-line" /></div><h1>Pause. Check.<br /><em>Protect each other.</em></h1><p className="hero-lede">A suspicious message reached you. Let’s check the warning signs together before you click, pay or share.</p>
          <div className="hero-proof"><div className="proof-avatars"><span>J</span><span>M</span><span>A</span><span>+</span></div><p><b>Shared vigilance starts here.</b><br />One check can help the next person.</p></div>
          <div className="hero-secondary"><span className={`api-dot ${apiOnline ? 'online' : ''}`} />{apiOnline ? 'ScamDar community is connected' : 'Connecting to ScamDar…'}</div>
        </div>
        <div className="checker-card"><div className="checker-heading"><div><span className="step-label">01 / CHECK</span><h2>What did you receive?</h2></div><span className="checker-icon"><Icon name="search" size={21} /></span></div>
          <p className="checker-help">Paste a message, suspicious link, phone number or email. Your check is private unless you choose to report it.</p>
          <form onSubmit={runCheck}><label className="sr-only" htmlFor="message-check">Suspicious message or link</label><textarea id="message-check" maxLength={8000} value={text} onChange={e => setText(e.target.value)} placeholder="Paste the suspicious message or link here…" />
            <div className="textarea-footer"><span>{text.length.toLocaleString()} / 8,000</span><button type="button" className="text-action" onClick={() => { setText(DEMO_TEXT); setError(''); setAnalysis(null) }}>Try the demo message <Icon name="arrow" size={15} /></button></div>
            <div className="checker-buttons"><button className="primary-button" type="submit" disabled={loading || !apiOnline}>{loading ? <span className="spinner" /> : <Icon name="shield" size={18} />}{loading ? 'Checking…' : 'Check for scam'}</button><button type="button" className="upload-button" onClick={() => document.getElementById('screenshot-input')?.click()}><Icon name="upload" size={17} /> Screenshot</button><input id="screenshot-input" className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" onChange={async event => { const file = event.target.files?.[0]; if (!file) return; const data = new FormData(); data.append('file', file); setLoading(true); setError(''); try { const result = await api('/api/analyze/screenshot', { method: 'POST', body: data }); setAnalysis(result); setText(result.extracted_text || '') } catch (e) { setError(e.message) } finally { setLoading(false); event.target.value = '' } }} /></div>
          </form>
          {error && <div className="inline-error" role="alert"><Icon name="alert" size={17} />{error}</div>}
          <div className="privacy-note"><Icon name="shield" size={15} /><span>Your message is analysed privately. It is only shared if you choose to report it.</span><button className="text-action" onClick={() => user ? setReportOpen(true) : setAuthOpen(true)}>Report a scam</button></div>
        </div></section>
        {analysis && <section className="analysis-panel" aria-live="polite"><div className="analysis-top"><div><span className="step-label">YOUR CHECK RESULTS</span><h2>Here’s what ScamDar noticed</h2><p>Each point comes from a visible signal in the message.</p></div><button className="icon-button" onClick={() => setAnalysis(null)} aria-label="Close result"><Icon name="close" /></button></div>
          <div className="analysis-content"><div className={`score-card score-${analysis.level.toLowerCase()}`}><div className="score-orbit"><div className="score-number">{analysis.score}<small>/100</small></div></div><RiskPill level={analysis.level} /><p>{analysis.recommended_action}</p><span className="score-footnote">Technical risk estimate · community opinion shown separately</span></div>
            <div className="signals-column"><div className="signals-header"><h3>Warning signs</h3><span>{analysis.signals.length} signals found</span></div>{analysis.signals.length ? analysis.signals.map(signal => <div key={signal.code} className="signal-row"><span className="signal-check"><Icon name="alert" size={15} /></span><div><b>{signal.label}</b><p>{signal.detail}</p></div><span className="signal-points">+{signal.points}</span></div>) : <div className="empty-signals"><Icon name="check" />No strong scam signals found. Stay cautious with unexpected requests.</div>}
              <div className="disclaimer">{analysis.disclaimer}</div>
            </div></div>
          {analysis.similar_reports?.length > 0 && <div className="similar-section"><div className="section-heading compact"><div><span className="step-label">COMMUNITY EVIDENCE</span><h3>Similar reports from the community</h3></div><span className="match-count">{analysis.similar_reports.length} matches</span></div><div className="similar-grid">{analysis.similar_reports.slice(0, 3).map(report => <button className="similar-card" key={report.id} onClick={() => inspectReport(report)}><div className="similar-card-top"><span className="category-tag">{pretty(report.category)}</span><span>{report.similarity}% match</span></div><b>{report.title}</b><p>{report.content.slice(0, 110)}{report.content.length > 110 ? '…' : ''}</p><div className="similar-card-foot"><RiskPill level={report.risk_level} /><span>{report.region}</span></div></button>)}</div></div>}
          <div className="analysis-actions"><button className="primary-button" onClick={() => user ? setReportOpen(true) : setAuthOpen(true)}><Icon name="plus" size={18} />Report this message</button><button className="outline-button" onClick={() => navigator.clipboard?.writeText(shareText).then(() => setToast('Warning copied to clipboard.')).catch(() => setToast('Copy is not available in this browser.'))}><Icon name="share" size={17} />Copy warning</button><a className="whatsapp-button" href={`https://wa.me/?text=${encodeURIComponent(shareText)}`} target="_blank" rel="noreferrer"><span>↗</span> Share to WhatsApp</a><button className="outline-button" onClick={() => user ? setTrustedOpen(true) : setAuthOpen(true)}><Icon name="people" size={17} />Ask someone I trust</button></div>
        </section>}
        <section className="three-promises"><div><span className="promise-icon"><Icon name="shield" /></span><div><b>Explainable by design</b><p>See the warning signs behind each score.</p></div></div><div><span className="promise-icon"><Icon name="people" /></span><div><b>Stronger together</b><p>Community reports help surface repeat campaigns.</p></div></div><div><span className="promise-icon"><Icon name="map" /></span><div><b>Privacy stays broad</b><p>Regional trends never show exact addresses.</p></div></div></section>
        <section className="home-feed"><div className="section-heading"><div><span className="step-label">FROM THE COMMUNITY</span><h2>Warnings worth sharing</h2></div><button className="text-action" onClick={() => setPage('feed')}>View community feed <Icon name="arrow" size={15} /></button></div><FeedCards items={feed.slice(0, 3)} onSelect={inspectReport} onBrowse={() => setPage('feed')} /></section>
      </>}

      {page === 'feed' && <section className="page-wrap"><PageIntro eyebrow="COMMUNITY RADAR" title="Warnings shared by people like you" description="Real encounters help the next person spot a pattern. Community votes are shown separately from ScamDar’s technical risk estimate." action={<button className="primary-button" onClick={() => user ? setReportOpen(true) : setAuthOpen(true)}><Icon name="plus" />Report a scam</button>} />
        <div className="feed-toolbar"><label>Category<select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}>{categories.map(cat => <option value={cat} key={cat}>{cat === 'all' ? 'All categories' : pretty(cat)}</option>)}</select></label><label>Region<select value={filterRegion} onChange={e => setFilterRegion(e.target.value)}><option value="all">All regions</option>{REGIONS.map(region => <option key={region}>{region}</option>)}</select></label><label>Sort by<select value={sort} onChange={e => setSort(e.target.value)}><option value="newest">Newest</option><option value="trending">Trending</option><option value="most-reported">Most reported</option></select></label><span className="results-count">{feed.length} reports</span></div>
        <FeedCards items={feed} onSelect={inspectReport} onBrowse={() => loadFeed()} /></section>}

      {page === 'trends' && <section className="page-wrap"><PageIntro eyebrow="COMMUNITY SIGNALS" title="See the patterns, not just one message" description="A broad view of what neighbours are reporting. Community evidence is informative, not proof." /><TrendDashboard trends={trends} /></section>}
      {page === 'map' && <section className="page-wrap"><PageIntro eyebrow="REGIONAL AWARENESS" title="Scam activity across Singapore" description="Reports are grouped into broad regions. ScamDar never collects or displays a victim’s home address." /><RegionalMap trends={trends} /></section>}
      {page === 'admin' && user && ['moderator', 'admin'].includes(user.role) && <section className="page-wrap"><PageIntro eyebrow="SAFETY OPERATIONS" title="Moderation and community health" description="Review reports that people flagged, record a resolution, and check the audit trail." /><AdminDashboard summary={adminSummary} flags={moderationFlags} users={adminUsers} isAdmin={user.role === 'admin'} onResolve={moderateFlag} onRole={setRole} onMerge={mergeFlaggedReport} onWarn={warnUser} /></section>}
      {page === 'trusted' && <section className="page-wrap"><TrustedResponsePage token={trustedToken} /></section>}
    </main>
    <footer className="site-footer"><div className="footer-main"><Brand /><p>Waze crowdsources road danger.<br /><b>ScamDar crowdsources digital danger.</b></p><div className="footer-cta"><span>Have a suspicious message?</span><button onClick={() => { setPage('check'); window.scrollTo({ top: 0, behavior: 'smooth' }) }}>Check it with ScamDar <Icon name="arrow" size={15} /></button></div></div><div className="footer-bottom"><span>© 2026 ScamDar · HackIT 2026 project demo</span><span>Not an official government or financial service. Verify through trusted official channels.</span><button onClick={() => setToast('Use the official bank or agency app to verify anything involving money or account access.')}>Safety guidance</button></div></footer>

    {selected && <ReportDialog report={selected} comments={comments} onClose={() => setSelected(null)} onVote={sendVote} onHelpful={helpfulComment} onComment={addComment} onShare={() => window.open(`https://wa.me/?text=${encodeURIComponent(shareText)}`, '_blank', 'noopener,noreferrer')} onFlag={async (targetType = 'report', targetId = selected.id) => { if (!user) { setAuthOpen(true); return } const reason = window.prompt('Why should moderators review this content?'); if (!reason) return; try { await api('/api/flags', { method: 'POST', body: JSON.stringify({ target_type: targetType, target_id: targetId, reason }) }); setToast('Flag sent to moderators.') } catch (e) { setToast(e.message) } }} user={user} />}
    {authOpen && <Modal title={authMode === 'login' ? 'Welcome back' : 'Join ScamDar'} subtitle={authMode === 'login' ? 'Sign in to report, vote and join a discussion.' : 'Help turn one scam encounter into protection for the next person.'} onClose={() => { setAuthOpen(false); setError('') }}><form className="modal-form" onSubmit={authSubmit}>{authMode === 'signup' && <label>Your name<input name="display_name" required minLength="2" maxLength="60" placeholder="How should we call you?" /></label>}<label>Email address<input name="email" type="email" autoComplete="email" required placeholder="you@example.com" /></label><label>Password<input name="password" type="password" autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'} minLength={authMode === 'signup' ? 10 : 1} required placeholder={authMode === 'signup' ? 'At least 10 characters' : 'Your password'} /></label>{error && <div className="inline-error"><Icon name="alert" />{error}</div>}<button className="primary-button full-width" type="submit">{authMode === 'login' ? 'Sign in' : 'Create account'} <Icon name="arrow" size={17} /></button><p className="form-switch">{authMode === 'login' ? 'New to ScamDar?' : 'Already have an account?'} <button type="button" onClick={() => { setAuthMode(authMode === 'login' ? 'signup' : 'login'); setError('') }}>{authMode === 'login' ? 'Create an account' : 'Sign in'}</button></p><small className="form-privacy">Your account is used for community actions. Public scam checks do not require sign-in.</small></form></Modal>}
    {reportOpen && <Modal title="Share a scam warning" subtitle="Help the community notice the pattern. Leave out names, account numbers and exact addresses." onClose={() => setReportOpen(false)}><form className="modal-form report-form" onSubmit={createReport}><label>Suspicious message or description<textarea name="content" required minLength="12" maxLength="8000" defaultValue={analysis ? text : ''} placeholder="Paste the message, with personal information removed…" /></label><div className="form-two"><label>Category<select name="category" defaultValue={analysis?.category || 'other'}>{CATEGORIES.map(cat => <option key={cat} value={cat}>{pretty(cat)}</option>)}</select></label><label>Broad region<select name="region" defaultValue="Singapore-wide">{REGIONS.map(region => <option key={region}>{region}</option>)}</select></label></div><div className="form-two"><label>Suspicious URL (optional)<input name="url" type="url" maxLength="2048" placeholder="https://…" /></label><label>Phone number (optional)<input name="phone" maxLength="40" placeholder="Remove personal numbers first" /></label></div><label>Impersonated brand (optional)<input name="impersonated_brand" maxLength="80" placeholder="e.g. delivery company or bank" /></label><button className="primary-button full-width" type="submit"><Icon name="plus" />Submit community report</button><small className="form-privacy">Reports are public to the community and can be flagged for review. Only broad regions are stored.</small></form></Modal>}
    {trustedOpen && <Modal title="Ask someone you trust" subtitle="A second opinion can help you pause. ScamDar creates a private response link for you to share." onClose={() => { setTrustedOpen(false); setTrustedLink('') }}><form className="modal-form" onSubmit={askContact}><label>Trusted contact email<input name="email" type="email" required placeholder="someone you trust@example.com" /></label><label>Message to review<textarea name="message" minLength="3" maxLength="1000" defaultValue={text} required placeholder="Paste the message you want a second opinion on…" /></label><button className="primary-button full-width">Create private response link</button>{trustedLink && <div className="share-link-box"><p>Share this link privately with your trusted contact:</p><code>{trustedLink}</code><button type="button" onClick={() => navigator.clipboard.writeText(trustedLink).then(() => setToast('Trusted contact link copied.'))}>Copy link</button></div>}<small className="form-privacy">This demo does not send email. The response link expires after 7 days.</small></form></Modal>}
    {toast && <div className="toast" role="status"><Icon name="check" size={17} />{toast}<button onClick={() => setToast('')} aria-label="Dismiss"><Icon name="close" size={16} /></button></div>}
  </div>
}

function PageIntro({ eyebrow, title, description, action }) { return <div className="page-intro"><div><span className="step-label">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action && <div>{action}</div>}</div> }

function FeedCards({ items, onSelect, onBrowse }) {
  if (!items?.length) return <div className="empty-feed"><span><Icon name="people" size={24} /></span><h3>Community reports are loading</h3><p>When connected, the latest synthetic and community reports appear here.</p>{onBrowse && <button className="outline-button" onClick={onBrowse}>Refresh the feed</button>}</div>
  return <div className="feed-grid">{items.map(report => <button className="feed-card" key={report.id} onClick={() => onSelect(report)}><div className="feed-card-top"><span className="category-tag">{pretty(report.category)}</span><span className="feed-region"><Icon name="map" size={13} />{report.region}</span></div><h3>{report.title}</h3><p>{report.content.slice(0, 126)}{report.content.length > 126 ? '…' : ''}</p><div className="feed-card-bottom"><RiskPill level={report.risk_level} /><span>{humanDate(report.created_at)}</span><span className="feed-stat"><Icon name="people" size={14} />{report.vote_summary?.total || 0}</span><span className="feed-stat">{report.comment_count || 0} replies</span></div></button>)}</div>
}

function TrendDashboard({ trends }) {
  if (!trends) return <div className="empty-feed">Loading community patterns…</div>
  const max = Math.max(1, ...Object.values(trends.by_category || {}))
  return <><div className="trend-stats"><StatCard label="Reports today" value={trends.reports_today} note="Past 24 hours" icon="alert" /><StatCard label="This week" value={trends.reports_this_week} note="Past seven days" icon="chart" /><StatCard label="Active campaigns" value={trends.active_campaigns} note="Patterns being reported" icon="people" /></div><div className="trend-panels"><div className="trend-panel"><div className="panel-heading"><div><span className="step-label">REPORT MIX</span><h3>Reports by category</h3></div><span className="muted">All time</span></div>{Object.entries(trends.by_category || {}).map(([key, value]) => <div className="bar-row" key={key}><span>{pretty(key)}</span><div className="bar-track"><i style={{ width: `${Math.max(4, value / max * 100)}%` }} /></div><b>{value}</b></div>)}</div><div className="trend-panel"><div className="panel-heading"><div><span className="step-label">COMMONLY MENTIONED</span><h3>Impersonated organisations</h3></div></div>{Object.entries(trends.top_brands || {}).slice(0, 6).map(([key, value], i) => <div className="rank-row" key={key}><span className="rank-number">0{i + 1}</span><b>{key}</b><span className="rank-count">{value} reports</span></div>)}{!Object.keys(trends.top_brands || {}).length && <p className="muted">No reports yet.</p>}<p className="panel-footnote">Community mentions are unverified unless marked by a moderator.</p></div></div><p className="trend-note"><Icon name="shield" size={16} />{trends.note}</p></>
}

function StatCard({ label, value, note, icon }) { return <div className="stat-card"><span className="stat-icon"><Icon name={icon} /></span><span className="stat-label">{label}</span><strong>{value}</strong><small>{note}</small></div> }

function RegionalMap({ trends }) {
  const values = trends?.by_region || {}
  const max = Math.max(1, ...Object.values(values))
  const regions = [{ name: 'North', x: 155, y: 38 }, { name: 'North East', x: 250, y: 76, key: 'Northeast' }, { name: 'Central', x: 132, y: 145 }, { name: 'East', x: 284, y: 156 }, { name: 'West', x: 44, y: 145 }, { name: 'Singapore-wide', x: 165, y: 226 }]
  return <div className="map-layout"><div className="map-card"><div className="map-legend"><span><i className="legend-low" />Fewer reports</span><span><i className="legend-high" />More reports</span></div><svg className="singapore-map" viewBox="0 0 360 290" role="img" aria-label="Abstract broad-region activity map of Singapore"><path d="M69 70 112 41 169 34 218 55 271 73 305 113 293 167 264 200 222 231 165 251 113 225 76 192 47 150 51 108z" fill="#e8eee7" stroke="#d4ded5" strokeWidth="2"/><path d="m112 41 18 69 35-76m-35 76 88-55m-88 55 87 0m-87 0-53 40m53-40-17 77m104-77 56-37m-56 37 45 44m-45-44-17 86m17-86 76 0m-76 0 42 77m-42-77-42 86m0-86-18 77m18-77-70 0" fill="none" stroke="#d4ded5" strokeWidth="2"/>{regions.map(region => { const key = region.key || region.name; const count = values[key] || 0; const alpha = .16 + count / max * .42; return <g key={key}><circle cx={region.x} cy={region.y} r="28" fill={`rgba(192, 80, 53, ${alpha})`} /><circle cx={region.x} cy={region.y} r="20" fill="#fff" stroke="#e4e9e2" strokeWidth="1.5" /><text x={region.x} y={region.y + 4} textAnchor="middle" fontSize="12" fontWeight="700" fill="#173e35">{count}</text></g> })}</svg><p className="map-caption"><span className="api-dot online" />Broad region activity only · no victim locations displayed</p></div><div className="region-list"><span className="step-label">REGIONAL ACTIVITY</span><h3>Reports by area</h3>{regions.map(region => { const key = region.key || region.name; return <div className="region-row" key={key}><span className="region-marker" />{region.name}<b>{values[key] || 0}</b></div> })}<div className="region-safety"><Icon name="shield" size={17} /><p>Locations are grouped. No pins, postal codes or home addresses are collected.</p></div></div></div>
}

function AdminDashboard({ summary, flags, users, isAdmin, onResolve, onRole, onMerge, onWarn }) {
  if (!summary) return <div className="empty-feed">Loading moderation workspace…</div>
  return <><div className="trend-stats admin-summary-stats"><StatCard label="Community members" value={summary.users} note="Registered accounts" icon="people" /><StatCard label="Reports" value={summary.reports} note="Community and synthetic" icon="chart" /><StatCard label="Active campaigns" value={summary.active_campaigns} note="Grouped report patterns" icon="chart" /><StatCard label="Open flags" value={summary.open_flags} note="Awaiting review" icon="alert" /></div>
    <div className="admin-grid"><div className="trend-panel"><div className="panel-heading"><div><span className="step-label">REVIEW QUEUE</span><h3>Flagged content</h3></div><span className="muted">{flags.length} open</span></div>{flags.length ? flags.map(flag => <div className="admin-flag" key={flag.id}><div className="admin-flag-copy"><span className="category-tag">{pretty(flag.target_type)} #{flag.target_id}</span><b>{flag.reason}</b>{flag.details && <p>{flag.details}</p>}<small>Flag #{flag.id} · {humanDate(flag.created_at)}</small></div><div className="admin-flag-actions">{flag.target_type === 'report' && <><button onClick={() => onResolve(flag, 'verify')}>Verify</button><button onClick={() => onResolve(flag, 'lock')}>Lock</button><button onClick={() => onResolve(flag, 'hide')}>Hide</button><button onClick={() => onMerge(flag.target_id)}>Merge</button></>}{flag.target_user_id && <button onClick={() => onWarn(flag.target_user_id)}>Warn author</button>}<button onClick={() => onResolve(flag, 'dismiss')}>Dismiss</button></div></div>) : <p className="empty-comments">No open flags. The queue is clear.</p>}</div>
      <div className="trend-panel"><div className="panel-heading"><div><span className="step-label">LATEST REPORTS</span><h3>Community reports</h3></div></div>{summary.recent_reports?.length ? summary.recent_reports.map(report => <div className="rank-row" key={report.id}><span className="category-tag">#{report.id} · {pretty(report.category)}</span><b className="admin-report-title">{report.title}</b><RiskPill level={report.risk_level} /></div>) : <p className="empty-comments">No reports yet.</p>}</div></div>
      <div className="trend-panel admin-users"><div className="panel-heading"><div><span className="step-label">AUDIT TRAIL</span><h3>Recent actions</h3></div></div>{summary.recent_audit?.length ? summary.recent_audit.map((event, index) => <div className="rank-row" key={`${event.action}-${index}`}><span className="rank-number">{humanDate(event.created_at)}</span><b>{event.action.replaceAll('.', ' ')}</b><span className="rank-count">{event.target_type} {event.target_id ? `#${event.target_id}` : ''}</span></div>) : <p className="empty-comments">No moderator actions recorded yet.</p>}</div>
    {isAdmin && <div className="trend-panel admin-users"><div className="panel-heading"><div><span className="step-label">ACCESS CONTROL</span><h3>Users and roles</h3></div></div>{users.map(member => <div className="admin-user-row" key={member.id}><span className="user-avatar">{member.display_name.slice(0,1).toUpperCase()}</span><div><b>{member.display_name}</b><small>{member.email}</small></div><select value={member.role} onChange={event => onRole(member.id, event.target.value)} aria-label={`Role for ${member.display_name}`}><option value="user">User</option><option value="trusted_contributor">Trusted contributor</option><option value="moderator">Moderator</option><option value="admin">Admin</option></select><button className="text-action" onClick={() => onWarn(member.id)}>Warn</button></div>)}</div>}
    <p className="trend-note"><Icon name="shield" size={16} />Moderator actions are recorded. Review evidence before hiding, verifying, or merging a report.</p>
  </>
}

function TrustedResponsePage({ token }) {
  const [result, setResult] = useState('')
  const [error, setError] = useState('')
  async function respond(choice) {
    try { await api(`/api/trusted-contacts/${encodeURIComponent(token)}/respond`, { method: 'POST', body: JSON.stringify({ response: choice }) }); setResult(choice); setError('') }
    catch (e) { setError(e.message) }
  }
  return <div className="trusted-response-card"><span className="modal-mark"><Icon name="people" size={22} /></span><span className="step-label">A FRIEND ASKED YOU TO TAKE A LOOK</span><h1>Help someone pause before they act.</h1><p>Choose the response that best fits. This is a second opinion, not a guarantee that a message is safe or fraudulent.</p>{result ? <div className="trusted-done"><Icon name="check" />Your response “{result}” was shared with the person who asked.</div> : token ? <div className="trusted-choice-list">{['Do not proceed', 'Looks safe', 'I am unsure'].map(choice => <button key={choice} onClick={() => respond(choice)}>{choice}<Icon name="arrow" size={16} /></button>)}</div> : <div className="inline-error"><Icon name="alert" />This link is missing its private response token.</div>}{error && <div className="inline-error"><Icon name="alert" />{error}</div>}<a className="text-action" href="/">Return to ScamDar <Icon name="arrow" size={15} /></a></div>
}

function ReportDialog({ report, comments, onClose, onVote, onHelpful, onComment, onShare, onFlag, user }) {
  const [replyTo, setReplyTo] = useState(null)
  const counts = report.vote_summary?.counts || {}
  const choices = ['Scam', 'Not sure', 'Likely legitimate']
  return <div className="overlay" role="presentation" onMouseDown={event => event.target === event.currentTarget && onClose()}><section className="report-dialog" role="dialog" aria-modal="true" aria-labelledby="report-title"><div className="dialog-header"><span className="step-label">COMMUNITY REPORT · #{report.id}</span><button className="icon-button" onClick={onClose} aria-label="Close"><Icon name="close" /></button></div><div className="dialog-scroll"><div className="dialog-title-row"><div><span className="category-tag">{pretty(report.category)}</span><h2 id="report-title">{report.title}</h2></div><RiskPill level={report.risk_level} /></div><p className="report-content">{report.content}</p><div className="report-meta"><span><Icon name="map" size={14} />{report.region}</span><span>First seen {humanDate(report.created_at)}</span>{report.impersonated_brand && <span>Mentions {report.impersonated_brand}</span>}</div><div className="report-score-strip"><div><small>Technical risk</small><b>{report.score}/100 · {report.risk_level}</b></div><div><small>Community confidence</small><b>{report.vote_summary?.community_confidence == null ? 'No votes yet' : `${report.vote_summary.community_confidence}% voted Scam`}</b></div></div>
        <div className="vote-panel"><div><b>What do you think?</b><p>Your vote is separate from the technical score.</p></div><div className="vote-buttons">{choices.map(choice => <button key={choice} onClick={() => onVote(report.id, choice)}>{choice}<span>{counts[choice] || 0}</span></button>)}</div></div>
        <div className="discussion"><div className="panel-heading"><div><span className="step-label">COMMUNITY DISCUSSION</span><h3>Help each other spot the signs</h3></div><span>{comments.length} replies</span></div>{comments.length ? comments.map(comment => <div className={`comment-row ${comment.parent_id ? 'reply-row' : ''}`} key={comment.id}><span className="comment-avatar">{comment.author.slice(0,1).toUpperCase()}</span><div><b>{comment.author}</b><p>{comment.body}</p><small>{humanDate(comment.created_at)} · {comment.helpful_count || 0} found this helpful</small><div className="comment-actions"><button type="button" onClick={() => onHelpful(comment.id)}>Helpful</button>{!report.discussion_locked && <button type="button" onClick={() => setReplyTo(comment.id)}>Reply</button>}<button type="button" onClick={() => onFlag('comment', comment.id)}>Flag</button></div></div></div>) : <p className="empty-comments">No discussion yet. Add a helpful note or official verification tip.</p>}
          {report.discussion_locked ? <p className="locked-note">This discussion has been locked by a moderator.</p> : <form className="comment-form" onSubmit={onComment}>{replyTo && <div className="replying-note">Replying to comment #{replyTo}<button type="button" onClick={() => setReplyTo(null)}>Cancel</button></div>}<input type="hidden" name="parent_id" value={replyTo || ''} /><label className="sr-only" htmlFor="comment-input">Add a comment</label><input id="comment-input" name="body" maxLength="1200" placeholder={user ? 'Share a helpful note…' : 'Sign in to join the discussion'} /><button className="primary-button" type="submit">Reply <Icon name="arrow" size={15} /></button></form>}
        </div>
        <div className="dialog-actions"><button className="outline-button" onClick={onShare}><Icon name="share" size={16} />Share warning</button><button className="text-action" onClick={onFlag}><Icon name="alert" size={15} />Flag for review</button></div>
      </div></section></div>
}

function Modal({ title, subtitle, children, onClose }) { return <div className="overlay" role="presentation" onMouseDown={event => event.target === event.currentTarget && onClose()}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-top"><span className="modal-mark"><Icon name="compass" size={22} /></span><button className="icon-button" onClick={onClose} aria-label="Close"><Icon name="close" /></button></div><h2 id="modal-title">{title}</h2><p className="modal-subtitle">{subtitle}</p>{children}</section></div> }

export default App
