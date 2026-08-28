import {
  Badge,
  Button,
  Codicon,
  Loader,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  STATUSBAR_AREAS,
  Tip,
  cn,
  compactNumber,
  host,
  useQuery,
  useMutation,
  useQueryClient,
  useValue
} from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'
import { useEffect, useRef, useState } from 'react'

const ROUTE = '/sips-control-plane'
const SIPS_TAB_KEY = 'sips-control-plane-tab'
const API_STATUS = '/status'
const API_ACTIONS = '/actions'

const COLORS = {
  accent: 'var(--ui-accent, #7dd3fc)',
  good: 'var(--ui-success, #69d39a)',
  warn: 'var(--ui-warning, #f4c76b)',
  bad: 'var(--ui-danger, #f28b8b)',
  muted: 'var(--ui-text-tertiary, #98a2b3)',
  text: 'var(--ui-text-primary, #eef2f7)',
  panel: 'var(--ui-surface-raised, rgba(255,255,255,0.045))',
  border: 'var(--ui-border, rgba(255,255,255,0.10))'
}

const styles = {
  page: {
    boxSizing: 'border-box',
    position: 'relative',
    height: '100%',
    overflow: 'auto',
    padding: '28px 34px 48px',
    color: COLORS.text,
    background: 'var(--ui-surface, transparent)'
  },
  max: { maxWidth: '1180px', margin: '0 auto', position: 'relative', zIndex: 1 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '20px', marginBottom: '24px' },
  eyebrow: { color: COLORS.accent, fontSize: '12px', fontWeight: 700, letterSpacing: '0.13em', textTransform: 'uppercase' },
  title: { fontSize: '28px', lineHeight: 1.15, fontWeight: 700, margin: '6px 0 8px' },
  subtitle: { color: COLORS.muted, fontSize: '13px', lineHeight: 1.5, maxWidth: '700px' },
  actions: { display: 'flex', gap: '8px', alignItems: 'center', flexShrink: 0 },
  sectionGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '14px', alignItems: 'start' },
  card: { background: COLORS.panel, border: `1px solid ${COLORS.border}`, borderRadius: '14px', padding: '18px', marginBottom: '14px' },
  cardTitle: { display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 650, fontSize: '14px', marginBottom: '14px' },
  cardHint: { color: COLORS.muted, fontSize: '12px', margin: '-8px 0 14px' },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', padding: '8px 0', borderBottom: `1px solid ${COLORS.border}` },
  rowLast: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', padding: '8px 0' },
  label: { color: COLORS.muted, fontSize: '12px' },
  value: { fontSize: '12px', fontWeight: 600, textAlign: 'right' },
  objective: { fontSize: '17px', lineHeight: 1.4, fontWeight: 600, margin: '2px 0 16px' },
  progressTrack: { height: '7px', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden', margin: '8px 0 7px' },
  progressFill: { height: '100%', background: COLORS.good, borderRadius: '999px', transition: 'transform 200ms ease', transformOrigin: 'left center' },
  proof: { padding: '10px 11px', border: `1px solid ${COLORS.border}`, borderRadius: '10px' },
  proofName: { color: COLORS.muted, fontSize: '12px', marginBottom: '5px' },
  proofList: { display: 'grid', gap: '11px' },
  proofRow: { display: 'grid', gap: '6px' },
  proofRowHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' },
  miniTrack: { height: '5px', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden' },
  miniFill: { height: '100%', borderRadius: '999px', transition: 'transform 200ms ease', transformOrigin: 'left center' },
  hero: { position: 'relative', overflow: 'hidden', padding: '20px 22px 16px', marginBottom: '14px', background: 'linear-gradient(135deg, rgba(125,211,252,0.13), rgba(255,255,255,0.04) 48%, rgba(105,211,154,0.08))', border: `1px solid ${COLORS.border}`, borderRadius: '18px', boxShadow: '0 18px 44px rgba(0,0,0,0.16)' },
  heroGlow: { position: 'absolute', width: '220px', height: '220px', right: '-70px', top: '-110px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(125,211,252,0.2), transparent 70%)', pointerEvents: 'none' },
  heroLayout: { position: 'relative', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '24px' },
  heroIdentity: { minWidth: 0 },
  heroTitle: { fontSize: '21px', lineHeight: 1.2, fontWeight: 700, margin: '5px 0 7px', textWrap: 'balance' },
  heroText: { color: COLORS.muted, fontSize: '12px', lineHeight: 1.5, maxWidth: '650px', textWrap: 'pretty' },
  heroFooter: { display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginTop: '13px' },
  updated: { color: COLORS.muted, fontSize: '12px', fontVariantNumeric: 'tabular-nums' },
  readiness: { display: 'grid', justifyItems: 'center', gap: '6px', flexShrink: 0 },
  readinessOrb: { width: '82px', height: '82px', display: 'grid', placeItems: 'center', borderRadius: '50%', background: 'conic-gradient(var(--ui-success, #69d39a) 0%, rgba(255,255,255,0.1) 0)', boxShadow: '0 0 28px rgba(105,211,154,0.14)' },
  readinessOrbInner: { width: '66px', height: '66px', display: 'grid', placeItems: 'center', borderRadius: '50%', background: 'var(--ui-surface, #102b68)', textAlign: 'center' },
  readinessValue: { fontSize: '17px', lineHeight: 1, fontWeight: 750, fontVariantNumeric: 'tabular-nums' },
  readinessLabel: { color: COLORS.muted, fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', textAlign: 'center' },
  signalGrid: { position: 'relative', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(165px, 1fr))', gap: '8px', marginTop: '18px' },
  signal: { minWidth: 0, padding: '10px 11px', border: `1px solid ${COLORS.border}`, borderRadius: '11px', background: 'rgba(0,0,0,0.08)' },
  signalLabel: { color: COLORS.muted, fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em' },
  signalValue: { fontSize: '17px', fontWeight: 700, marginTop: '4px', fontVariantNumeric: 'tabular-nums' },
  signalDetail: { color: COLORS.muted, fontSize: '12px', marginTop: '3px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  signalTrack: { height: '4px', marginTop: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden' },
  sparkline: { display: 'block', width: '100%', height: '23px', marginTop: '7px', overflow: 'visible' },
  freshness: { display: 'inline-flex', alignItems: 'center', gap: '6px', color: COLORS.muted, fontSize: '12px', fontVariantNumeric: 'tabular-nums' },
  freshnessDot: { width: '6px', height: '6px', borderRadius: '50%', background: COLORS.good, boxShadow: '0 0 0 3px rgba(105,211,154,0.12)' },
  proofDetail: { marginTop: '7px', padding: '9px 10px', borderRadius: '9px', background: 'rgba(0,0,0,0.10)', color: COLORS.muted, fontSize: '12px', lineHeight: 1.45 },
  proofSummary: { cursor: 'pointer', listStyle: 'none' },
  eventToolbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '4px' },
  select: { minHeight: '32px', padding: '0 28px 0 9px', border: `1px solid ${COLORS.border}`, borderRadius: '8px', background: 'rgba(0,0,0,0.12)', color: COLORS.text, fontSize: '12px' },
  filterCount: { color: COLORS.muted, fontSize: '12px', fontVariantNumeric: 'tabular-nums' },
  actionGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '8px' },
  action: { display: 'grid', gap: '8px', padding: '11px', border: `1px solid ${COLORS.border}`, borderRadius: '10px', background: 'rgba(0,0,0,0.08)' },
  actionTitle: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 650 },
  actionDescription: { color: COLORS.muted, fontSize: '12px', lineHeight: 1.4 },
  actionButton: { minHeight: '40px', justifySelf: 'start' },
  actionResult: { marginTop: '10px', padding: '10px', borderRadius: '9px', border: `1px solid ${COLORS.border}`, background: 'rgba(0,0,0,0.10)', color: COLORS.muted, fontSize: '12px', lineHeight: 1.45 },
  actionResultError: { borderColor: COLORS.bad, color: COLORS.bad },
  proofAction: { minHeight: '36px', marginTop: '9px' },
  event: { position: 'relative', display: 'grid', gridTemplateColumns: '10px minmax(0, 1fr)', gap: '10px', padding: '9px 0 9px 1px', borderBottom: `1px solid ${COLORS.border}` },
  eventRail: { position: 'absolute', left: '4px', top: '18px', bottom: '-10px', width: '1px', background: COLORS.border },
  eventDot: { position: 'relative', zIndex: 1, width: '8px', height: '8px', borderRadius: '50%', background: COLORS.accent, marginTop: '4px', boxShadow: '0 0 0 3px rgba(125,211,252,0.1)' },
  eventBody: { minWidth: 0 },
  eventTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' },
  eventName: { fontSize: '12px', fontWeight: 650, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  eventTime: { color: COLORS.muted, fontSize: '12px', flexShrink: 0, fontVariantNumeric: 'tabular-nums' },
  eventMeta: { color: COLORS.muted, fontSize: '12px', marginTop: '3px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  memoryTrack: { height: '8px', display: 'flex', gap: '2px', margin: '5px 0 10px', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden' },
  memoryVerified: { height: '100%', background: COLORS.good },
  memoryOther: { height: '100%', background: 'rgba(255,255,255,0.18)' },
  empty: { border: `1px dashed ${COLORS.border}`, borderRadius: '11px', color: COLORS.muted, padding: '16px', fontSize: '12px', lineHeight: 1.5, background: 'rgba(0,0,0,0.06)' },
  unavailable: { border: `1px dashed ${COLORS.border}`, borderRadius: '10px', color: COLORS.muted, padding: '16px', fontSize: '12px', lineHeight: 1.5 },
  metaRow: { display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '7px', marginBottom: '12px', color: COLORS.muted, fontSize: '12px' },
  metaText: { color: COLORS.muted, fontSize: '12px', fontVariantNumeric: 'tabular-nums' },
  metaBadge: { fontSize: '12px', padding: '1px 7px' },
  controlRow: { display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' },
  input: { flex: '1 1 160px', minWidth: '140px', minHeight: '34px', padding: '0 10px', border: `1px solid ${COLORS.border}`, borderRadius: '8px', background: 'rgba(0,0,0,0.14)', color: COLORS.text, fontSize: '12px', boxSizing: 'border-box' },
  textarea: { width: '100%', minHeight: '58px', padding: '8px 10px', border: `1px solid ${COLORS.border}`, borderRadius: '8px', background: 'rgba(0,0,0,0.14)', color: COLORS.text, fontSize: '12px', lineHeight: 1.45, resize: 'vertical', boxSizing: 'border-box', fontFamily: 'inherit' },
  recallResult: { display: 'grid', gap: '4px', padding: '10px 11px', marginTop: '8px', border: `1px solid ${COLORS.border}`, borderRadius: '10px', background: 'rgba(0,0,0,0.10)' },
  recallTitle: { fontSize: '12px', fontWeight: 650, color: COLORS.text },
  recallBody: { color: COLORS.muted, fontSize: '12px', lineHeight: 1.45 },
  recallTags: { display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '2px' },
  routeGrid: { display: 'grid', gap: '6px' },
  routeRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px', padding: '7px 0', borderBottom: `1px solid ${COLORS.border}` },
  routeName: { fontSize: '12px', fontWeight: 650, fontFamily: 'ui-monospace, monospace' },
  routeTool: { color: COLORS.muted, fontSize: '12px', textAlign: 'right' },
  feedback: { marginTop: '9px', padding: '9px 10px', borderRadius: '9px', border: `1px solid ${COLORS.border}`, background: 'rgba(0,0,0,0.10)', color: COLORS.muted, fontSize: '12px', lineHeight: 1.45 },
  feedbackError: { borderColor: COLORS.bad, color: COLORS.bad },
  // Signature element: the tab rail. Amplifies what the system already owns —
  // the accent token, the eyebrow's uppercase tracking, tabular numerals — at
  // full strength. Underline motif (like the header rule) instead of boxes.
  tabBar: { position: 'sticky', top: '0', zIndex: 10, display: 'flex', gap: '20px', margin: '0 -34px 22px', padding: '10px 34px 0', borderBottom: `1px solid ${COLORS.border}`, background: 'var(--ui-surface, #14161b)' },
  tabBarLabel: { alignSelf: 'center', marginRight: '8px', color: COLORS.accent, fontSize: '12px', fontWeight: 700, letterSpacing: '0.13em', textTransform: 'uppercase' },
  tab: { position: 'relative', display: 'inline-flex', alignItems: 'center', gap: '7px', minHeight: '42px', padding: '0 2px', border: 0, background: 'transparent', color: COLORS.muted, fontSize: '13px', fontWeight: 700, letterSpacing: '0.02em', cursor: 'pointer', transition: 'color 150ms ease' },
  tabActive: { color: COLORS.text },
  tabActiveMark: { position: 'absolute', left: 0, right: 0, bottom: '-1px', height: '2px', background: COLORS.accent, borderRadius: '2px 2px 0 0' },
  tabCount: { minWidth: '18px', padding: '1px 6px', textAlign: 'center', fontSize: '12px', borderRadius: '999px', background: COLORS.warn, color: '#10131a', fontWeight: 700, fontVariantNumeric: 'tabular-nums' },
  // Tab grids: lead card spans full width; supporting cards share the row below.
  // Hierarchy follows task priority — the tab's reason-for-visit leads.
  tabGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px', alignItems: 'start' },
  leadRow: { marginBottom: '16px' },
  supportGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px', alignItems: 'start' },
  moreChecks: { marginTop: '10px', border: `1px solid ${COLORS.border}`, borderRadius: '10px', background: 'rgba(0,0,0,0.05)', padding: '9px 11px' },
  moreChecksSummary: { cursor: 'pointer', listStyle: 'none', color: COLORS.muted, fontSize: '12px', fontWeight: 650 },
  moreChecksGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '8px', margin: '10px 0 2px' },
  actionButtonRow: { display: 'flex', gap: '8px', justifySelf: 'start' },
  eventToggleRow: { display: 'flex', justifyContent: 'center', marginTop: '10px' },
  eventCapNote: { color: COLORS.muted, fontSize: '12px', textAlign: 'center', marginTop: '8px' },
  findingsMore: { marginTop: '5px' },
  findingsMoreSummary: { cursor: 'pointer', listStyle: 'none', color: COLORS.accent },
  // --- Depth system (layered elevation) ------------------------------------
  // Tier 1 recessed wells: darker inset surfaces for inputs, tracks, details.
  // Tier 2 resting cards: subtle drop shadow + top hairline highlight.
  // Tier 3 raised leads: hero + GoalCard, stronger shadow and light edge.
  cardElevated: {
    background: 'linear-gradient(180deg, rgba(255,255,255,0.028), rgba(255,255,255,0) 42%), rgba(0,0,0,0.10)',
    border: `1px solid ${COLORS.border}`,
    borderTopColor: 'rgba(255,255,255,0.16)',
    boxShadow: '0 1px 2px rgba(0,0,0,0.18), 0 6px 18px rgba(0,0,0,0.14)'
  },
  cardLead: {
    background: 'linear-gradient(180deg, rgba(255,255,255,0.038), rgba(255,255,255,0) 46%), rgba(0,0,0,0.14)',
    border: `1px solid rgba(255,255,255,0.13)`,
    borderTopColor: 'rgba(255,255,255,0.20)',
    boxShadow: '0 2px 4px rgba(0,0,0,0.22), 0 14px 34px rgba(0,0,0,0.24)'
  },
  hoverLift: {
    transition: 'transform 180ms cubic-bezier(0.2, 0.7, 0.3, 1), box-shadow 180ms cubic-bezier(0.2, 0.7, 0.3, 1), border-color 180ms ease'
  },
  wellInset: {
    boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.30)'
  },
  // --- Mission rail navigation ----------------------------------------------
  // Vertical workspace spine: raised surface like the leads, sticky, with a
  // live posture beacon and per-tab count badges.
  layout: { display: 'grid', gridTemplateColumns: '212px minmax(0, 1fr)', gap: '20px', alignItems: 'start' },
  rail: {
    position: 'sticky',
    top: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    padding: '14px 12px 12px',
    background: 'linear-gradient(180deg, rgba(255,255,255,0.03), rgba(0,0,0,0.12))',
    border: `1px solid ${COLORS.border}`,
    borderTopColor: 'rgba(255,255,255,0.18)',
    borderRadius: '16px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.20), 0 12px 30px rgba(0,0,0,0.22)'
  },
  railHead: { display: 'flex', alignItems: 'center', gap: '8px', padding: '2px 6px 11px', borderBottom: `1px solid ${COLORS.border}` },
  railDot: { width: '9px', height: '9px', borderRadius: '50%', flexShrink: 0 },
  railItems: { display: 'grid', gap: '4px' },
  railItem: {
    position: 'relative',
    display: 'grid',
    gridTemplateColumns: '18px minmax(0, 1fr) auto',
    alignItems: 'center',
    gap: '10px',
    minHeight: '40px',
    padding: '0 10px 0 15px',
    border: 0,
    borderRadius: '10px',
    background: 'transparent',
    color: COLORS.muted,
    fontSize: '13px',
    fontWeight: 650,
    textAlign: 'left',
    cursor: 'pointer'
  },
  railItemMark: { position: 'absolute', left: '5px', top: '25%', bottom: '25%', width: '3px', borderRadius: '999px', background: COLORS.accent, boxShadow: `0 0 8px ${COLORS.accent}` },
  workspace: { minWidth: 0 },
  // --- Instrument bank ------------------------------------------------------
  // The dashboard as a physical machine: machined panels, beveled edges,
  // switches, dials, hinged doors. Light comes from above.
  module: {
    position: 'relative',
    background: 'repeating-linear-gradient(180deg, rgba(255,255,255,0.012) 0 1px, transparent 1px 3px), linear-gradient(180deg, #262a33, #1a1d24 58%, #16191e)',
    border: '1px solid rgba(0,0,0,0.65)',
    borderTopColor: 'rgba(255,255,255,0.18)',
    borderLeftColor: 'rgba(255,255,255,0.09)',
    borderRadius: '12px',
    padding: '18px',
    boxShadow: '0 2px 3px rgba(0,0,0,0.5), 0 10px 26px rgba(0,0,0,0.4), inset 0 -3px 8px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.07)'
  },
  moduleLead: {
    background: 'repeating-linear-gradient(180deg, rgba(255,255,255,0.014) 0 1px, transparent 1px 3px), linear-gradient(180deg, #2a2e38, #1c1f27 55%, #181b21)',
    boxShadow: '0 3px 5px rgba(0,0,0,0.55), 0 16px 40px rgba(0,0,0,0.48), inset 0 -4px 10px rgba(0,0,0,0.48), inset 0 1px 0 rgba(255,255,255,0.08)'
  },
  screwPlate: { position: 'absolute', top: '8px', right: '10px', display: 'flex', gap: '6px', zIndex: 3 },
  screw: {
    width: '9px', height: '9px', borderRadius: '50%',
    background: 'linear-gradient(45deg, transparent 44%, rgba(20,22,26,0.9) 46% 54%, transparent 56%), radial-gradient(circle at 35% 30%, #565c66, #20242a 72%)',
    boxShadow: 'inset 0 1px 1px rgba(255,255,255,0.25), inset 0 -1px 1px rgba(0,0,0,0.6), 0 1px 1px rgba(0,0,0,0.6)'
  },
  gaugeWrap: { position: 'relative', width: '96px', height: '96px', flexShrink: 0 },
  dialFace: {
    position: 'absolute', inset: 0, borderRadius: '50%',
    background: 'radial-gradient(circle at 42% 34%, #2c3038, #191c22 72%)',
    border: '1px solid rgba(0,0,0,0.6)',
    boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5), inset 0 -1px 0 rgba(255,255,255,0.05), 0 2px 5px rgba(0,0,0,0.4)'
  },
  dialTicks: { position: 'absolute', inset: 0, borderRadius: '50%' },
  dialNeedle: {
    position: 'absolute', left: '50%', bottom: '50%',
    width: '2.5px', height: '40%', marginLeft: '-1.25px',
    background: 'linear-gradient(180deg, var(--ui-danger, #f28b8b), rgba(242,139,139,0.25))',
    transformOrigin: 'bottom center',
    transition: 'transform 650ms cubic-bezier(0.16, 1, 0.3, 1)'
  },
  dialHub: {
    position: 'absolute', left: '50%', bottom: '50%', width: '11px', height: '11px', marginLeft: '-5.5px', marginBottom: '-5.5px',
    borderRadius: '50%', background: 'radial-gradient(circle at 38% 32%, #565c66, #21242b)',
    boxShadow: '0 1px 2px rgba(0,0,0,0.6)'
  },
  dialNeedleClass: 'sips-dial-needle',
  dialLabel: { textAlign: 'center', color: COLORS.muted, fontSize: '11px', marginTop: '6px', textTransform: 'uppercase', letterSpacing: '0.09em' },
  // Toggle switch (master power / selfloop).
  toggleSlot: {
    position: 'relative', width: '58px', height: '30px', borderRadius: '999px',
    background: '#101318',
    border: '1px solid rgba(0,0,0,0.65)',
    boxShadow: 'inset 0 2px 5px rgba(0,0,0,0.65), inset 0 -1px 0 rgba(255,255,255,0.05)',
    cursor: 'pointer', flexShrink: 0
  },
  toggleKnob: {
    position: 'absolute', top: '2px', left: '2px', width: '26px', height: '24px', borderRadius: '999px',
    background: 'linear-gradient(180deg, #4b515b, #2b2f37 60%, #22262d)',
    border: '1px solid rgba(0,0,0,0.5)',
    boxShadow: '0 2px 4px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.18)',
    transition: 'transform 150ms cubic-bezier(0.16, 1, 0.3, 1)'
  },
  toggleKnobClass: 'sips-toggle-knob',
  toggleOn: { transform: 'translateX(28px)' },
  // Push button (verification checks): deep recess + raised cap that visibly
  // depresses on :active via the stylesheet hook.
  pushBtn: {
    appearance: 'none', border: '1px solid rgba(0,0,0,0.65)', padding: '9px 14px', cursor: 'pointer',
    display: 'inline-grid', placeItems: 'center', gap: '4px',
    minHeight: '54px', borderRadius: '10px',
    background: 'repeating-linear-gradient(180deg, rgba(255,255,255,0.01) 0 1px, transparent 1px 3px), #101318',
    boxShadow: 'inset 0 3px 7px rgba(0,0,0,0.7), inset 0 -1px 0 rgba(255,255,255,0.05)',
    color: COLORS.muted, fontSize: '12px', fontWeight: 650,
    transition: 'box-shadow 90ms ease, transform 90ms ease, color 90ms ease'
  },
  pushCap: {
    display: 'grid', placeItems: 'center',
    width: '26px', height: '26px', borderRadius: '50%',
    background: 'linear-gradient(180deg, #4b515b, #262a31)',
    border: '1px solid rgba(0,0,0,0.55)',
    boxShadow: '0 2px 3px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.16)'
  },
  // Hinged proof-breaker door.
  breaker: { perspective: '900px', borderRadius: '10px' },
  breakerFrame: {
    position: 'relative', borderRadius: '10px', overflow: 'hidden',
    background: '#14171d',
    border: '1px solid rgba(0,0,0,0.6)',
    boxShadow: 'inset 0 2px 5px rgba(0,0,0,0.5)'
  },
  breakerDoor: {
    position: 'relative', zIndex: 2, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px',
    padding: '12px 13px',
    background: 'repeating-linear-gradient(180deg, rgba(255,255,255,0.015) 0 1px, transparent 1px 3px), linear-gradient(180deg, #31353f, #22252d)',
    border: '1px solid rgba(0,0,0,0.6)', borderTopColor: 'rgba(255,255,255,0.16)', borderLeftColor: 'rgba(255,255,255,0.08)',
    borderRadius: '10px', transformOrigin: 'top center',
    transition: 'transform 280ms cubic-bezier(0.55, 0, 0.7, 0.35), box-shadow 280ms ease',
    boxShadow: '0 3px 5px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.09)'
  },
  breakerOpen: { transform: 'rotateX(-78deg)', boxShadow: '0 -1px 3px rgba(0,0,0,0.3)' },
  breakerInterior: {
    position: 'absolute', inset: 0, zIndex: 1, padding: '11px 12px', paddingTop: '46px',
    background: '#101318', color: COLORS.muted, fontSize: '12px', lineHeight: 1.45
  },
  // Paper tape (activity stream).
  tapeStrip: {
    background: 'repeating-linear-gradient(180deg, #f4efe4, #f4efe4 26px, #ece6da 27px)',
    color: '#33302a', borderRadius: '6px', padding: '12px 14px',
    boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.18), 0 3px 8px rgba(0,0,0,0.35)',
    fontVariantNumeric: 'tabular-nums'
  },
  tapeRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px',
    padding: '5px 0', borderBottom: '1px dashed rgba(51,48,42,0.25)', fontSize: '12px'
  }
}

function toneFor(value) {
  const normalized = String(value || '').toLowerCase()
  if (['inspected', 'active', 'done', 'verified', 'connected', 'ready', 'healthy', 'ok', 'source_present'].includes(normalized)) return 'good'
  if (['not_inspected', 'paused', 'pending', 'unknown', 'loading', 'legacy', 'advisory_unavailable'].includes(normalized)) return 'warn'
  if (normalized.includes('unproven') || ['partial', 'stale', 'degraded', 'incomplete'].includes(normalized)) return 'warn'
  if (['not_found', 'source_not_found', 'failed', 'error', 'blocked'].includes(normalized)) return 'bad'
  return 'muted'
}

// ---------------------------------------------------------------------------
// Motion primitives — Living Proof overdrive layer.
// Every helper respects prefers-reduced-motion by snapping instantly.
// ---------------------------------------------------------------------------

const SIPS_REDUCED_MOTION = () =>
  typeof window !== 'undefined' && Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)

// Minimal spring solver: rAF-driven animation of a numeric value.
// Returns a cancel function. Snaps when reduced motion is preferred.
function springTo({ from, to, onFrame, stiffness = 170, damping = 22, onDone }) {
  if (typeof window === 'undefined') { onFrame(to); if (onDone) onDone(); return () => {} }
  if (SIPS_REDUCED_MOTION()) { onFrame(to); if (onDone) onDone(); return () => {} }
  let value = from
  let velocity = 0
  let raf = 0
  let last = performance.now()
  const step = (now) => {
    const dt = Math.min((now - last) / 1000, 1 / 30)
    last = now
    const force = (to - value) * stiffness
    velocity += force * dt
    velocity *= Math.exp(-damping * dt)
    value += velocity * dt
    if (Math.abs(to - value) < 0.1 && Math.abs(velocity) < 0.1) {
      onFrame(to)
      if (onDone) onDone()
      return
    }
    onFrame(value)
    raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
  return () => cancelAnimationFrame(raf)
}

// Lerp between two hex colors for posture hue morphs.
function lerpColor(fromHex, toHex, t) {
  const parse = (hex) => {
    const clean = String(hex || '').replace('#', '')
    if (!/^[0-9a-fA-F]{6}$/.test(clean)) return [153, 162, 179]
    return [parseInt(clean.slice(0, 2), 16), parseInt(clean.slice(2, 4), 16), parseInt(clean.slice(4, 6), 16)]
  }
  const a = parse(fromHex)
  const b = parse(toHex)
  const mix = a.map((channel, i) => Math.round(channel + (b[i] - channel) * t))
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`
}

const SIPS_TONE_HEX = { good: '#69d39a', warn: '#f4c76b', bad: '#f28b8b', muted: '#98a2b3' }

// Evidence-gated celebration: fires at most once per minute, only when the
// persisted proof trend genuinely advanced. Fire-and-forget overlay.
let sipsLastCelebrate = 0
function celebrateProofGain(orbElement, valueElement, fromCoverage, toCoverage) {
  if (typeof document === 'undefined' || SIPS_REDUCED_MOTION()) return
  const now = Date.now()
  if (now - sipsLastCelebrate < 60000) return
  sipsLastCelebrate = now
  try {
    if (orbElement?.animate) {
      orbElement.animate(
        [{ boxShadow: '0 0 0 0 rgba(105,211,154,0.45)' }, { boxShadow: '0 0 0 26px rgba(105,211,154,0)' }],
        { duration: 900, easing: 'ease-out', iterations: 1 }
      )
    }
    if (valueElement) {
      springTo({
        from: fromCoverage,
        to: toCoverage,
        stiffness: 120,
        damping: 18,
        onFrame: (v) => { valueElement.textContent = `${Math.round(v)}%` }
      })
    }
  } catch { /* animation unavailable — the state change itself already rendered */ }
}

// Quiet-hours guard: ambient motion stops after 10 minutes without interaction.
let sipsLastInteraction = Date.now()
if (typeof window !== 'undefined') {
  const markInteraction = () => { sipsLastInteraction = Date.now() }
  window.addEventListener('pointerdown', markInteraction, { passive: true })
  window.addEventListener('keydown', markInteraction, { passive: true })
}
const SIPS_AWAKE = () => Date.now() - sipsLastInteraction < 10 * 60 * 1000

function formatTimestamp(value) {
  if (!value) return 'just now'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'recently'

  // Include the date for anything not from today so old events are distinguishable.
  const now = new Date()
  const sameDay = date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate()
  return new Intl.DateTimeFormat(undefined, sameDay
    ? { hour: 'numeric', minute: '2-digit' }
    : { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date)
}

function formatRelativeTimestamp(value) {
  if (!value) return 'just now'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'recently'

  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000))
  if (seconds < 10) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`
  return formatTimestamp(value)
}

function formatStatus(value) {
  return String(value || 'unknown').replaceAll('_', ' ')
}

function percent(value, total) {
  if (!total) return 0
  return Math.max(0, Math.min(100, Math.round((Number(value) / Number(total)) * 100)))
}

function postureFor(data) {
  const proofEntries = Object.entries(data?.proof_layers || {})
  const readyProof = proofEntries.filter(([, value]) => toneFor(value) === 'good').length
  const coverage = percent(readyProof, proofEntries.length)
  const sourceTone = toneFor(data?.status)

  if (sourceTone === 'bad') return { label: 'unhealthy', tone: 'bad', coverage, readyProof, totalProof: proofEntries.length }
  if (proofEntries.length && coverage === 100 && sourceTone === 'good') return { label: 'ready', tone: 'good', coverage, readyProof, totalProof: proofEntries.length }
  if (proofEntries.length && coverage < 100) return { label: 'partial', tone: 'warn', coverage, readyProof, totalProof: proofEntries.length }
  return { label: 'unverified', tone: 'warn', coverage, readyProof, totalProof: proofEntries.length }
}

function postureCopy(posture, sourceStatus) {
  if (posture.tone === 'bad') return 'SIPS reported an unhealthy source. Review the proof layers and recent lifecycle events.'
  if (posture.label === 'partial') return `Source is ${formatStatus(sourceStatus)}. Expand the proof layers below to see what each one establishes — and what it does not.`
  if (posture.label === 'ready') return 'Source and evidence layers are reporting a complete local operational posture.'
  return 'Read-only telemetry from the SIPS control plane; evidence coverage is not complete yet.'
}

function trendLabel(values, unit = 'pts') {
  if (!values || values.length < 2) return 'Collecting trend'
  const delta = Number(values[values.length - 1]) - Number(values[0])
  if (Math.abs(delta) < 0.5) return 'Stable'
  const rounded = Math.round(Math.abs(delta) * 10) / 10
  return `${delta > 0 ? '+' : '-'}${rounded}${unit} over ${values.length} samples`
}

function Sparkline({ values, color = COLORS.accent }) {
  if (!values || values.length < 2) return jsx('div', { style: styles.signalDetail, children: 'Collecting trend' })

  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const points = values.map((value, index) => `${(index / (values.length - 1)) * 100},${22 - ((value - min) / span) * 18}`).join(' ')

  return jsx('svg', {
    viewBox: '0 0 100 24',
    preserveAspectRatio: 'none',
    ariaHidden: true,
    style: styles.sparkline,
    children: [
      jsx('line', { x1: '0', y1: '22', x2: '100', y2: '22', stroke: 'rgba(255,255,255,0.10)', strokeWidth: '1' }),
      jsx('polyline', { points, fill: 'none', stroke: color, strokeWidth: '2', strokeLinecap: 'round', strokeLinejoin: 'round' })
    ]
  })
}

function toneColor(value) {
  return COLORS[toneFor(value)] || COLORS.muted
}

function StateBadge({ value, tone }) {
  const color = tone ? COLORS[tone] : toneColor(value)

  return jsx(Badge, {
    variant: 'outline',
    style: { color, borderColor: color, fontSize: '12px' },
    children: formatStatus(value)
  })
}

function Card({ title, icon, hint, lead = false, children }) {
  return jsx('section', {
    style: { ...styles.card, ...(lead ? styles.moduleLead : styles.module) },
    'data-sips-card': true,
    'data-sips-lead': lead ? true : undefined,
    children: [
      jsx('div', { style: styles.screwPlate, 'aria-hidden': true, children: [jsx('span', { style: styles.screw }), jsx('span', { style: styles.screw })] }),
      jsx('div', { style: styles.cardTitle, children: [jsx(Codicon, { name: icon, size: '0.95rem' }), jsx('span', { children: title })] }),
      hint ? jsx('div', { style: styles.cardHint, children: hint }) : null,
      children
    ]
  })
}

// Analog dial gauge: needle sweeps -120°..+120° for value 0..100. Springs via
// CSS transition; snaps under reduced motion.
function Dial({ value, color, label, size = 96 }) {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0))
  const angle = -120 + (clamped / 100) * 240
  const ticks = []
  for (let i = 0; i <= 8; i++) {
    const tickAngle = -120 + (i / 8) * 240
    ticks.push(jsx('div', {
      key: i,
      style: {
        position: 'absolute', left: '50%', top: '50%', width: '1.5px',
        height: i % 2 === 0 ? '9px' : '6px',
        marginLeft: '-0.75px',
        background: i % 2 === 0 ? COLORS.muted : 'rgba(152,162,179,0.45)',
        transformOrigin: 'center top',
        transform: `translateY(-${size * 0.40}px) rotate(${tickAngle}deg) translateY(${size * 0.40}px)`
      }
    }))
  }
  return jsx('div', { style: { ...styles.gaugeWrap, width: `${size}px`, height: `${size}px` }, role: 'img', 'aria-label': `${label}: ${clamped}%`, children: [
    jsx('div', { style: styles.dialFace }),
    jsx('div', { style: { ...styles.dialTicks, transform: 'rotate(180deg)' }, children: ticks }),
    jsx('div', {
      className: 'sips-dial-needle',
      style: {
        ...styles.dialNeedle,
        background: `linear-gradient(180deg, ${color}, ${color}44)`,
        transform: `rotate(${angle}deg)`
      }
    }),
    jsx('div', { style: styles.dialHub }),
    jsx('div', {
      style: { position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', paddingTop: '26px' },
      children: jsx('span', { style: { fontSize: '15px', fontWeight: 750, fontVariantNumeric: 'tabular-nums', color }, children: `${clamped}%` })
    })
  ] })
}

// Toggle switch. controlled: `on` + `onToggle`.
function Toggle({ on, onToggle, label }) {
  return jsxs('button', {
    type: 'button',
    role: 'switch',
    'aria-checked': on,
    'aria-label': label,
    onClick: onToggle,
    style: styles.toggleSlot,
    children: [
      jsx('span', {
        'aria-hidden': true,
        style: { position: 'absolute', inset: 0, borderRadius: '999px', background: on ? 'rgba(105,211,154,0.18)' : 'transparent', transition: 'background 160ms ease' }
      }),
      jsx('span', { className: 'sips-toggle-knob', style: { ...styles.toggleKnob, ...(on ? styles.toggleOn : {}) } })
    ]
  })
}

// Momentary push button: cap visually depresses while pressed/running.
function PushButton({ label, running, disabled, onClick, tone }) {
  const capColor = running ? (COLORS[tone] || COLORS.accent) : undefined
  return jsxs('button', {
    type: 'button',
    'data-sips-push': true,
    disabled,
    onClick,
    style: { ...styles.pushBtn, ...(running ? { color: COLORS.text } : {}) },
    children: [
      jsx('span', { style: { ...styles.pushCap, ...(capColor ? { background: `linear-gradient(180deg, ${capColor}, #262a31)`, boxShadow: `0 0 8px ${capColor}66, inset 0 1px 0 rgba(255,255,255,0.16)` } : {}) } }),
      jsx('span', { children: running ? 'Running…' : label })
    ]
  })
}

// Circuit breaker: hinged metal door over a recessed interior. Click the door
// to swing it open and read what the layer establishes.
function Breaker({ title, badge, summary, boundary, action, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return jsx('div', {
    style: styles.breaker,
    children: jsxs('div', { style: styles.breakerFrame, children: [
      jsx('div', { style: { ...styles.breakerInterior }, children: [
        jsx('div', { style: { color: COLORS.text, marginBottom: '4px' }, children: summary }),
        jsx('div', { children: boundary }),
        action
      ] }),
      jsxs('div', {
        role: 'button',
        tabIndex: 0,
        'aria-expanded': open,
        onClick: () => setOpen((v) => !v),
        onKeyDown: (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setOpen((v) => !v) } },
        style: { ...styles.breakerDoor, ...(open ? styles.breakerOpen : {}) },
        children: [
          jsx('span', { style: { fontWeight: 650, fontSize: '12px' }, children: title }),
          jsx('span', { style: { display: 'inline-flex', alignItems: 'center', gap: '7px' }, children: [
            badge,
            jsx(Codicon, { name: open ? 'chevron-up' : 'chevron-down', size: '0.8rem' })
          ] })
        ]
      })
    ] })
  })
}


function Signal({ label, value, detail, tone = 'accent', progress, trend, trendUnit = 'pts' }) {
  const color = tone === 'accent' ? COLORS.accent : toneColor(tone)

  return jsx('div', {
    style: styles.signal,
    children: [
      jsx('div', { style: styles.signalLabel, children: label }),
      jsx('div', { style: { ...styles.signalValue, color }, children: value }),
      jsx('div', { style: styles.signalDetail, title: detail, children: detail }),
      progress === undefined ? null : jsx('div', {
        style: styles.signalTrack,
        children: jsx('div', { style: { ...styles.miniFill, width: `${progress}%`, background: color } })
      }),
      trend ? jsx('div', { title: trendLabel(trend, trendUnit), children: jsx(Sparkline, { values: trend, color }) }) : null
    ]
  })
}

// Posture helpers for the ambient atmosphere layer.
function postureToneOf(data) {
  return postureFor(data).tone
}

function postureCoverageOf(data) {
  return postureFor(data).coverage
}

const SIPS_ATMO_TONE = {
  good: { hue: 'rgba(105,211,154,0.16)', soft: 'rgba(125,211,252,0.10)', period: '11s', alpha: 0.5 },
  warn: { hue: 'rgba(244,199,107,0.15)', soft: 'rgba(244,199,107,0.07)', period: '7s', alpha: 0.55 },
  bad: { hue: 'rgba(242,139,139,0.18)', soft: 'rgba(242,139,139,0.08)', period: '3.6s', alpha: 0.65 },
  muted: { hue: 'rgba(152,162,179,0.10)', soft: 'rgba(125,211,252,0.07)', period: '12s', alpha: 0.4 }
}

// Ambient-reactive depth: a fixed blur field behind the page content whose hue
// and breathing period encode live posture (good/partial/unhealthy). Motion
// respects quiet-hours and reduced motion by freezing at a static wash.
function AtmosphereLayer({ tone, coverage }) {
  const config = SIPS_ATMO_TONE[tone] || SIPS_ATMO_TONE.muted
  const reduced = SIPS_REDUCED_MOTION()
  const awake = SIPS_AWAKE()
  const alpha = reduced || !awake ? Math.min(config.alpha, 0.35) : config.alpha
  // Coverage nudges intensity: fuller proof coverage reads calmer (slower,
  // fainter). Unhealthy posture breathes fast and slightly stronger.
  const coverageDamp = 1 - (Number(coverage) || 0) / 260

  return jsx('div', {
    'data-sips-atmosphere': true,
    style: {
      '--sips-atmo-hue': config.hue,
      '--sips-atmo-hue-soft': config.soft,
      '--sips-atmo-period': `${reduced ? 12 : parseFloat(config.period) / Math.max(0.55, coverageDamp)}s`,
      '--sips-atmo-alpha': String(Math.max(0.2, alpha * coverageDamp))
    }
  })
}

function StatusOverview({ data, history, updatedAt, isFetching, fetchError, selfloopActive }) {
  const posture = postureFor(data)
  const counts = data?.surface_counts || {}
  const surfaceTotal = Object.values(counts).reduce((sum, value) => sum + (Number(value) || 0), 0)
  const memory = data?.memory || {}
  const postureColor = COLORS[posture.tone] || COLORS.muted
  // Freshness clock lives HERE, not in Dashboard: a 1s tick anywhere else
  // re-renders every card on the page. Only the hero pays for the ticking.
  const [clock, setClock] = useState(Date.now())
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  const ageSeconds = updatedAt ? Math.max(0, Math.floor((clock - updatedAt) / 1000)) : undefined
  // Prefer the persisted proof trend (survives restarts) over session-local samples.
  const persistedProofTrend = Array.isArray(data?.proof_trend) && data.proof_trend.length >= 2 ? data.proof_trend : null
  const proofTrend = persistedProofTrend || history.map((sample) => sample.proofCoverage)
  const freshnessText = isFetching
    ? `Refreshing · ${ageSeconds === undefined ? 'awaiting data' : `${ageSeconds}s old`}`
    : fetchError
      ? `Stale · ${ageSeconds === undefined ? 'unknown age' : `${ageSeconds}s old`}`
      : ageSeconds === undefined
        ? 'Awaiting first update'
        : ageSeconds < 30 ? `Live · ${ageSeconds}s ago` : `Stale · ${ageSeconds}s ago`
  const freshnessColor = fetchError || (ageSeconds !== undefined && ageSeconds >= 60) ? COLORS.warn : COLORS.good
  const surfaceTrend = history.map((sample) => sample.surfaceTotal)
  const memoryTrend = history.map((sample) => sample.memoryVerified)
  const lifecycleTrend = history.map((sample) => sample.lifecycle)

  // --- Living Proof layer -------------------------------------------------
  const orbRef = useRef(null)
  const orbValueRef = useRef(null)
  const orbStateRef = useRef({ coverage: null, tone: posture.tone })
  const [celebratedAt, setCelebratedAt] = useState(null)

  // Orb springs to new coverage; hue morphs on posture change.
  useEffect(() => {
    if (!orbRef.current) return
    const previous = orbStateRef.current
    const element = orbRef.current
    if (previous.coverage === null || SIPS_REDUCED_MOTION()) {
      previous.coverage = posture.coverage
      element.style.setProperty('--sips-orb', `${posture.coverage}%`)
      return undefined
    }
    springTo({
      from: previous.coverage,
      to: posture.coverage,
      stiffness: 140,
      damping: 20,
      onFrame: (v) => element.style.setProperty('--sips-orb', `${v}%`)
    })
    previous.coverage = posture.coverage
    return undefined
  }, [posture.coverage])

  useEffect(() => {
    if (!orbRef.current) return
    const previous = orbStateRef.current
    if (previous.tone === posture.tone) return
    const fromHex = SIPS_TONE_HEX[previous.tone] || SIPS_TONE_HEX.muted
    const toHex = SIPS_TONE_HEX[posture.tone] || SIPS_TONE_HEX.muted
    if (SIPS_REDUCED_MOTION()) {
      orbRef.current.style.background = `conic-gradient(${toHex} var(--sips-orb), rgba(255,255,255,0.1) 0)`
    } else {
      springTo({
        from: 0,
        to: 1,
        stiffness: 90,
        damping: 20,
        onFrame: (t) => {
          const mixed = lerpColor(fromHex, toHex, t)
          orbRef.current.style.background = `conic-gradient(${mixed} var(--sips-orb), rgba(255,255,255,0.1) 0)`
        }
      })
    }
    previous.tone = posture.tone
  }, [posture.tone])

  // Evidence-gated celebration: only when the persisted trend advanced.
  useEffect(() => {
    const trend = Array.isArray(data?.proof_trend) ? data.proof_trend : []
    if (trend.length < 2) return
    const prev = Number(trend[trend.length - 2])
    const curr = Number(trend[trend.length - 1])
    if (!(curr > prev)) return
    celebrateProofGain(orbRef.current, orbValueRef.current, prev / Math.max(1, trend.length ? posture.totalProof : 1) * 100, posture.coverage)
    setCelebratedAt(Date.now())
  }, [data?.proof_trend])
  // -------------------------------------------------------------------------

  return jsx('section', {
    style: { ...styles.hero, ...styles.cardLead },
    'data-sips-card': true,
    'data-sips-lead': true,
    'data-sips-selfloop': selfloopActive && SIPS_AWAKE() ? 'on' : 'off',
    children: [
      jsx('div', { style: styles.heroGlow }),
      jsx('div', {
        'data-sips-heartbeat': selfloopActive && SIPS_AWAKE() ? 'on' : 'off',
        style: { position: 'absolute', inset: 0, borderRadius: '18px', pointerEvents: 'none', background: `radial-gradient(420px 200px at 85% 0%, ${SIPS_TONE_HEX[posture.tone] || SIPS_TONE_HEX.muted}1a, transparent 70%)` }
      }),
      jsx('div', {
        style: styles.heroLayout,
        children: [
          jsx('div', {
            style: styles.heroIdentity,
            children: [
              jsx('div', { style: styles.eyebrow, children: 'LIVE SIPS TELEMETRY' }),
              jsx('h2', { style: styles.heroTitle, children: 'System posture' }),
              jsx('p', { style: styles.heroText, children: postureCopy(posture, data?.status) }),
              jsx('div', {
                style: styles.heroFooter,
                children: [
                  jsx(StateBadge, { value: posture.label, tone: posture.tone }),
                  jsx('span', { style: styles.updated, children: `Source ${formatStatus(data?.status)}` }),
                  jsx('span', { style: { ...styles.freshness, color: freshnessColor }, children: [jsx('span', { style: { ...styles.freshnessDot, background: freshnessColor, boxShadow: '0 0 0 3px rgba(105,211,154,0.12)' } }), freshnessText] })
                ]
              })
            ]
          }),
          jsx('div', {
            style: styles.readiness,
            children: [
              jsx('div', { style: { display: 'flex', alignItems: 'center', gap: '18px' }, children: [
                jsx(Dial, { value: posture.coverage, color: SIPS_TONE_HEX[posture.tone] || SIPS_TONE_HEX.muted, label: 'proof coverage' }),
                jsx('div', { style: { textAlign: 'left' }, children: [
                  jsx('div', { style: { fontSize: '17px', fontWeight: 750, fontVariantNumeric: 'tabular-nums', color: postureColor }, children: `${posture.readyProof}/${posture.totalProof || 0}` }),
                  jsx('div', { style: styles.dialLabel, children: 'layers ready' })
                ] })
              ] })
            ]
          })
        ]
      }),
      jsx('div', {
        style: styles.signalGrid,
        children: [
          jsx(Signal, { label: 'Proof coverage', value: `${posture.coverage}%`, detail: `${posture.readyProof} of ${posture.totalProof || 0} layers ready`, tone: posture.tone, progress: posture.coverage, trend: proofTrend }),
          jsx(Signal, { label: 'Surface area', value: compactNumber(surfaceTotal), detail: `${trendLabel(surfaceTrend, '')} · declared capabilities`, trend: surfaceTrend, trendUnit: '' }),
          jsx(Signal, { label: 'Memory verified', value: compactNumber(memory.verified_or_active_count || 0), detail: memory.available ? `${compactNumber(memory.record_count || 0)} total records` : 'memory unavailable', tone: memory.available ? 'good' : 'warn', trend: memoryTrend, trendUnit: '' }),
          jsx(Signal, { label: 'Lifecycle', value: compactNumber(data?.events?.event_count || 0), detail: `${trendLabel(lifecycleTrend, '')} · recorded events`, trend: lifecycleTrend, trendUnit: '' })
        ]
      })
    ]
  })
}

function useSipsActions(api, data, statusError) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: ({ id, runTests = false }) => api.rest(`${API_ACTIONS}/${id}`, { method: 'POST', body: { run_tests: runTests } }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['sips-control-plane', 'status'] })
      queryClient.invalidateQueries({ queryKey: ['sips-control-plane', 'actions'] })
      if (result?.ok) {
        host.notify({ kind: 'success', title: 'SIPS check complete', message: `${formatStatus(result.status || 'completed')} · evidence snapshot refreshed` })
      } else {
        host.notify({ kind: 'warning', title: 'SIPS check needs attention', message: formatStatus(result?.status || 'failed') })
      }
    },
    onError: (error) => host.notifyError(error, 'SIPS action failed')
  })

  return {
    actions: data?.actions || [],
    proofActions: data?.proof_actions || {},
    loading: !data,
    error: Boolean(statusError),
    result: mutation.data,
    busy: mutation.isPending || mutation.isLoading,
    busyId: mutation.variables?.id,
    retry: () => queryClient.invalidateQueries({ queryKey: ['sips-control-plane', 'status'] }),
    run: (id, runTests = false) => mutation.mutate({ id, runTests })
  }
}

function ActionResult({ result }) {
  if (!result) return null

  const findings = Array.isArray(result.summary?.findings) ? result.summary.findings : []
  const proof = result.summary?.proof_layers
  const statusTone = result.ok ? toneFor(result.status) : 'bad'
  const shownFindings = findings.slice(0, 8)
  const extraFindings = findings.slice(8)

  // Delight at the earned moment: if this run's snapshot shows more ready
  // layers than the last history entry, acknowledge it in copy — proportional,
  // evidence-tied, gone on the next run. No animation needed; the orb already
  // celebrates real gains.
  const readyStates = ['inspected', 'active', 'done', 'verified', 'connected', 'ready', 'healthy', 'ok', 'source_present']
  const readyCount = proof ? Object.values(proof).filter((value) => readyStates.includes(String(value).toLowerCase())).length : null

  return jsx('div', {
    style: { ...styles.actionResult, ...(result.ok ? {} : styles.actionResultError) },
    children: [
      jsx('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px' }, children: [jsx(StateBadge, { value: result.status, tone: statusTone }), jsx('span', { style: styles.updated, children: `Completed ${formatRelativeTimestamp(result.completed_at)}` })] }),
      result.claim_boundary ? jsx('div', { children: result.claim_boundary }) : null,
      readyCount !== null ? jsx('div', { style: { marginTop: '5px', color: COLORS.good, fontSize: '12px', fontWeight: 650 }, children: `${readyCount} of ${Object.keys(proof).length} proof layers now report ready.` }) : null,
      shownFindings.length ? jsxs('div', { style: { marginTop: '7px' }, children: [
        ...shownFindings.map((finding, index) => jsx('div', { key: index, children: `• ${typeof finding === 'string' ? finding : finding.detail || finding.message || JSON.stringify(finding)}` })),
        extraFindings.length ? jsx('details', {
          style: styles.findingsMore,
          children: [
            jsx('summary', {
              style: styles.findingsMoreSummary,
              children: `+${extraFindings.length} more findings`
            }),
            ...extraFindings.map((finding, index) => jsx('div', { key: `extra-${index}`, children: `• ${typeof finding === 'string' ? finding : finding.detail || finding.message || JSON.stringify(finding)}` }))
          ]
        }) : null
      ] }) : null,
      proof ? jsx('div', { style: { marginTop: '7px' }, children: `Proof snapshot: ${Object.entries(proof).map(([name, value]) => `${formatStatus(name)}=${formatStatus(value)}`).join(' · ')}` }) : null
    ]
  })
}

function ActionCenter({ actionState }) {
  if (actionState.loading) {
    return jsx(Card, { title: 'Next checks', icon: 'verified', hint: 'Loading allowlisted SIPS inspections…', children: jsx('div', { style: styles.unavailable, children: 'Preparing the action catalog.' }) })
  }
  if (actionState.error) {
    return jsxs(Card, { title: 'Next checks', icon: 'verified', children: [
      jsx('div', { style: styles.unavailable, children: 'The SIPS action catalog is unavailable. Refresh the dashboard to retry.' }),
      jsx(Button, { variant: 'outline', size: 'sm', onClick: () => actionState.retry(), style: styles.actionButton, children: 'Retry' })
    ] })
  }

  if (!actionState.actions.length) {
    return jsx(Card, { title: 'Next checks', icon: 'verified', hint: 'The current status payload did not advertise any allowlisted action.', children: jsx('div', { style: styles.unavailable, children: 'No SIPS actions are currently advertised.' }) })
  }

  const recommended = actionState.actions.filter((action) => action.recommended)
  const primary = recommended.length ? recommended : actionState.actions
  const rest = actionState.actions.filter((action) => !primary.includes(action))
  const renderAction = (action) => jsxs('div', {
    style: styles.action,
    key: action.id,
    children: [
      jsx('div', { style: styles.actionTitle, children: [jsx('span', { children: action.label }), action.recommended ? jsx(StateBadge, { value: 'recommended', tone: 'accent' }) : null] }),
      jsx('div', { style: { ...styles.actionDescription, marginBottom: '9px' }, children: action.description }),
      jsx('div', {
        style: styles.actionButtonRow,
        children: [
          jsx(PushButton, {
            label: 'Run check',
            tone: 'accent',
            running: actionState.busy && actionState.busyId === action.id,
            disabled: actionState.busy,
            onClick: () => actionState.run(action.id)
          }),
          action.id === 'verify_source' ? jsx(PushButton, {
            label: 'Run + tests',
            tone: 'good',
            running: actionState.busy && actionState.busyId === action.id,
            disabled: actionState.busy,
            onClick: () => actionState.run(action.id, true)
          }) : null
        ]
      })
    ]
  })

  return jsxs(Card, {
    title: 'Next checks',
    icon: 'verified',
    hint: recommended.length ? `Recommended from the currently unresolved proof layers${rest.length ? `, plus ${rest.length} more checks` : ''}. These actions are bounded inspections/probes.` : 'Allowlisted SIPS inspections and probes.',
    children: [
      jsx('div', {
        style: styles.actionGrid,
        children: primary.map(renderAction)
      }),
      rest.length ? jsx('details', {
        style: styles.moreChecks,
        children: [
          jsx('summary', { style: styles.moreChecksSummary, children: `More checks (${rest.length})` }),
          jsx('div', { style: styles.moreChecksGrid, children: rest.map(renderAction) })
        ]
      }) : null,
      recommended.length > 1 ? jsx(Button, {
        variant: 'outline',
        size: 'sm',
        disabled: actionState.busy,
        onClick: () => { for (const action of recommended) actionState.run(action.id) },
        style: { ...styles.actionButton, marginTop: '10px' },
        children: actionState.busy ? 'Running checks…' : `Run all ${recommended.length} recommended`
      }) : null,
      jsx(ActionResult, { result: actionState.result })
    ]
  })
}

function useSipsMutation(api, { invalidateKeys = [], onSuccess } = {}) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ path, method = 'POST', body }) => api.rest(path, { method, body }),
    onSuccess: (result, variables) => {
      for (const key of invalidateKeys) {
        queryClient.invalidateQueries({ queryKey: ['sips-control-plane', key] })
      }
      if (onSuccess) onSuccess(result, variables)
    },
    onError: (error) => host.notifyError(error, 'SIPS operation failed')
  })
}

function GoalSubtasks({ api }) {
  const goalQuery = useQuery({ queryKey: ['sips-control-plane', 'goal'], queryFn: () => api.rest('/goal'), refetchInterval: 30000 })
  const [newDescription, setNewDescription] = useState('')
  const [optimisticDone, setOptimisticDone] = useState({})
  const addMutation = useSipsMutation(api, { invalidateKeys: ['goal', 'status'] })
  const completeMutation = useSipsMutation(api, { invalidateKeys: ['goal', 'status'] })

  const subtasks = (goalQuery.data?.subtask_list || []).map((subtask) => ({
    ...subtask,
    status: optimisticDone[subtask.id] === true ? 'done' : optimisticDone[subtask.id] === false ? 'pending' : subtask.status
  }))
  const busy = completeMutation.isPending || addMutation.isPending

  return jsxs('div', { style: { marginTop: '12px', display: 'grid', gap: '6px' }, children: [
    jsx('div', { style: styles.label, children: 'Subtasks' }),
    subtasks.length ? subtasks.map((subtask) => jsxs('div', {
      style: styles.routeRow,
      children: [
        jsxs('span', {
          style: { display: 'inline-flex', alignItems: 'center', gap: '8px', minWidth: 0, ...(subtask.status === 'done' ? { textDecoration: 'line-through', color: COLORS.muted } : {}) },
          children: [
            jsx('button', {
              type: 'button',
              'aria-label': `Complete ${subtask.description}`,
              disabled: busy || subtask.status === 'done',
              onClick: () => {
                setOptimisticDone((current) => ({ ...current, [subtask.id]: true }))
                completeMutation.mutate(
                  { path: '/goal/subtask/complete', body: { id: subtask.id } },
                  { onError: () => setOptimisticDone((current) => ({ ...current, [subtask.id]: false })) }
                )
              },
              style: { width: '18px', height: '18px', borderRadius: '5px', border: `1px solid ${subtask.status === 'done' ? COLORS.good : COLORS.border}`, background: subtask.status === 'done' ? COLORS.good : 'transparent', color: '#10131a', cursor: subtask.status === 'done' ? 'default' : 'pointer', fontSize: '11px', lineHeight: 1, flexShrink: 0 },
              children: subtask.status === 'done' ? '✓' : ''
            }),
            jsx('span', { style: styles.recallBody, title: subtask.description, children: subtask.description })
          ]
        }),
        jsx('span', { style: styles.eventTime, children: subtask.status })
      ]
    }, `st-${subtask.id}`)) : jsx('span', { style: styles.recallBody, children: 'No subtasks yet.' }),
    jsxs('div', { style: styles.controlRow, children: [
      jsx('input', {
        style: styles.input,
        value: newDescription,
        placeholder: 'Add a subtask…',
        'aria-label': 'New subtask description',
        onChange: (event) => setNewDescription(event.target.value),
        onKeyDown: (event) => {
          if (event.key === 'Enter' && newDescription.trim() && !busy) {
            addMutation.mutate({ path: '/goal/subtask', body: { description: newDescription.trim() } })
            setNewDescription('')
          }
        }
      }),
      jsx(Button, {
        variant: 'outline', size: 'sm',
        disabled: busy || !newDescription.trim(),
        onClick: () => { addMutation.mutate({ path: '/goal/subtask', body: { description: newDescription.trim() } }); setNewDescription('') },
        children: 'Add'
      })
    ] })
  ] })
}

function SelfloopControls({ api, onMutated }) {
  const [focus, setFocus] = useState('')
  const [outcome, setOutcome] = useState('improved')
  const [summary, setSummary] = useState('')
  const [feedback, setFeedback] = useState(null)
  const mutation = useSipsMutation(api, {
    invalidateKeys: ['selfloop', 'status'],
    onSuccess: (result, variables) => {
      setFeedback(result?.ok
        ? `Selfloop ${variables.action} completed.`
        : `Selfloop ${variables.action} failed: ${result?.error || 'unknown error'}`)
      setFocus('')
      setSummary('')
      if (onMutated) onMutated()
    }
  })
  const busy = mutation.isPending || mutation.isLoading
  const run = (action, extra = {}) => mutation.mutate({ path: '/selfloop', body: { action, ...extra } })

  return jsx('div', {
    style: { marginTop: '13px', display: 'grid', gap: '8px' },
    children: [
      jsx('div', {
        style: styles.controlRow,
        children: [
          jsx('input', {
            style: styles.input,
            value: focus,
            placeholder: 'New goal focus (optional)…',
            'aria-label': 'Selfloop goal focus',
            onChange: (event) => setFocus(event.target.value)
          }),
          jsx(Button, { variant: 'outline', size: 'sm', disabled: busy, onClick: () => run('start', { focus }), children: 'Start' }),
          jsx(Button, { variant: 'outline', size: 'sm', disabled: busy, onClick: () => run('pause'), children: 'Pause' }),
          jsx(Button, { variant: 'outline', size: 'sm', disabled: busy, onClick: () => run('resume'), children: 'Resume' }),
          jsx(Button, { variant: 'outline', size: 'sm', disabled: busy, onClick: () => run('complete'), children: 'Complete' }),
          jsx(Button, { variant: 'outline', size: 'sm', disabled: busy, onClick: () => run('clear'), children: 'Clear' })
        ]
      }),
      jsx('div', {
        style: styles.controlRow,
        children: [
          jsx('select', {
            value: outcome,
            'aria-label': 'Cycle outcome',
            onChange: (event) => setOutcome(event.target.value),
            style: styles.select,
            children: ['improved', 'plateau', 'blocked'].map((value) => jsx('option', { value, key: value, children: value }))
          }),
          jsx('input', {
            style: styles.input,
            value: summary,
            placeholder: 'Cycle summary (optional)…',
            'aria-label': 'Cycle summary',
            onChange: (event) => setSummary(event.target.value)
          }),
          jsx(Button, { variant: 'outline', size: 'sm', disabled: busy, onClick: () => run('record', { outcome, summary }), children: 'Record cycle' })
        ]
      }),
      feedback ? jsx('div', { style: { ...styles.feedback, ...(String(feedback).includes('failed') ? styles.feedbackError : {}) }, children: feedback }) : null
    ]
  })
}

function GoalCard({ goal, api, selfloop, onSelfloopMutated }) {
  const controls = jsx(SelfloopControls, { api, onMutated: onSelfloopMutated })
  const selfloopMutation = useSipsMutation(api, {
    invalidateKeys: ['selfloop', 'status'],
    onSuccess: () => { if (onSelfloopMutated) onSelfloopMutated() }
  })
  const runSelfloop = (action) => selfloopMutation.mutate({ path: '/selfloop', body: { action } })

  if (!goal?.available) {
    const loopActive = selfloop?.active && selfloop?.state?.objective
    return jsx(Card, {
      title: 'Goal loop',
      icon: 'target',
      lead: true,
      children: [
        jsx('div', {
          style: styles.empty,
          children: [
            jsx('div', { style: { color: COLORS.text, fontWeight: 650, marginBottom: '5px' }, children: 'Awaiting an active goal' }),
            jsx('div', { children: loopActive ? `Selfloop is active: ${selfloop.state.objective}` : 'The loop will appear here when /goal or /selfloop creates one. This is an empty state, not a failure.' })
          ]
        }),
        controls
      ]
    })
  }

  const total = goal.subtasks?.total || 0
  const done = goal.subtasks?.done || 0
  const progress = total ? Math.round((done / total) * 100) : goal.status === 'done' ? 100 : 0
  const goalColor = toneColor(goal.status)
  // Cycle strip: last recorded cycle + streak from action history.
  const lastCycleAt = null // populated by HistoryCard data; kept simple here

  return jsx(Card, {
    title: 'Goal loop',
    icon: 'target',
    lead: true,
    hint: `${goal.mode || 'legacy'} mode · ${goal.turn_count || 0} turns · ${goal.cycle_count || 0} cycles`,
    children: [
      jsx('div', {
        style: { display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '13px' },
        children: [
          jsx(Dial, { value: progress, color: goalColor, label: 'subtask progress', size: 84 }),
          jsx('div', {
            style: { minWidth: 0, flex: 1 },
            children: [
              jsx('div', { style: styles.objective, children: goal.objective || 'Untitled goal' }),
              jsxs('div', { style: { ...styles.rowLast }, children: [
                jsx('span', { style: styles.label, children: 'State' }),
                jsx(StateBadge, { value: goal.status }),
                jsx(Toggle, {
                  on: Boolean(selfloop?.active),
                  onToggle: () => runSelfloop(selfloop?.active ? 'pause' : 'resume'),
                  label: selfloop?.active ? 'Pause selfloop' : 'Resume selfloop'
                })
              ] })
            ]
          })
        ]
      }),
      jsx('div', {
        style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' },
        children: [jsx('span', { style: styles.label, children: 'Subtask progress' }), jsx('span', { style: { ...styles.value, fontVariantNumeric: 'tabular-nums' }, children: `${done}/${total || 0}` })]
      }),
      jsx('div', { style: styles.progressTrack, children: jsx('div', { style: { ...styles.progressFill, width: `${progress}%`, background: goalColor } }) }),
      goal.current_subtask ? jsx('div', { style: { ...styles.label, marginTop: '8px' }, children: `Next: ${goal.current_subtask}` }) : null,
      goal.plateau_streak ? jsx('div', { style: { ...styles.rowLast, marginTop: '8px' }, children: [jsx('span', { style: styles.label, children: 'Plateau streak' }), jsx('span', { style: { ...styles.value, color: COLORS.warn, fontVariantNumeric: 'tabular-nums' }, children: goal.plateau_streak })] }) : null,
      jsx(GoalSubtasks, { api }),
      controls
    ]
  })
}

function RecallCard({ api }) {
  const [queryText, setQueryText] = useState('')
  const mutation = useSipsMutation(api)
  const result = mutation.data
  const busy = mutation.isPending || mutation.isLoading

  return jsx(Card, {
    title: 'Memory recall',
    icon: 'search',
    hint: 'Search scoped SIPS lessons; retrieval gates do not prove the selected claims.',
    children: [
      jsxs('div', {
        style: styles.controlRow,
        children: [
          jsx('input', {
            style: styles.input,
            value: queryText,
            placeholder: 'Query the SIPS memory fabric…',
            'aria-label': 'Recall query',
            onChange: (event) => setQueryText(event.target.value),
            onKeyDown: (event) => {
              if (event.key === 'Enter' && queryText.trim() && !busy) {
                mutation.mutate({ path: '/recall', body: { query: queryText.trim(), limit: 5 } })
              }
            }
          }),
          jsx(Button, {
            variant: 'outline',
            size: 'sm',
            disabled: busy || !queryText.trim(),
            onClick: () => mutation.mutate({ path: '/recall', body: { query: queryText.trim(), limit: 5 } }),
            children: busy ? 'Searching…' : 'Search'
          })
        ]
      }),
      result?.records?.length ? result.records.map((record, index) => jsxs('div', {
        style: styles.recallResult,
        children: [
          jsx('div', { style: styles.recallTitle, children: record.title }),
          record.body ? jsx('div', { style: styles.recallBody, children: record.body }) : null,
          jsxs('div', { style: styles.recallTags, children: [
            jsx(StateBadge, { value: `${record.tier} · ${record.confidence}`, tone: record.status === 'verified' || record.status === 'active' ? 'good' : 'muted' }),
            ...(record.tags || []).map((tag) => jsx(Badge, { key: tag, variant: 'outline', style: styles.metaBadge, children: tag }))
          ] })
        ]
      }, `recall-${index}`)) : null,
      result && !result.records?.length ? jsx('div', { style: styles.unavailable, marginTop: '8px', children: `No SIPS lessons matched "${result.query}". This is an empty result, not a failure.` }) : null,
      result?.ok === false ? jsx('div', { style: { ...styles.feedback, ...styles.feedbackError }, children: result.error || 'The recall search failed.' }) : null
    ]
  })
}

function RecordCard({ api, onRecorded }) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [tags, setTags] = useState('')
  const [tier, setTier] = useState('learning')
  const [feedback, setFeedback] = useState(null)
  const mutation = useSipsMutation(api, {
    invalidateKeys: ['status'],
    onSuccess: (result) => {
      setFeedback(result?.ok ? `Recorded "${title}".` : `Record failed: ${result?.error || 'unknown error'}`)
      if (result?.ok) {
        setTitle('')
        setBody('')
        setTags('')
        if (onRecorded) onRecorded()
      }
    }
  })
  const busy = mutation.isPending || mutation.isLoading

  return jsx(Card, {
    title: 'Record a lesson',
    icon: 'add',
    hint: 'Persists into the SIPS Memory Fabric; recording does not verify the lesson.',
    children: [
      jsx('input', {
        style: { ...styles.input, width: '100%', marginBottom: '8px' },
        value: title,
        placeholder: 'Lesson title…',
        'aria-label': 'Lesson title',
        onChange: (event) => setTitle(event.target.value)
      }),
      jsx('textarea', {
        style: styles.textarea,
        value: body,
        placeholder: 'What should SIPS remember?',
        'aria-label': 'Lesson body',
        onChange: (event) => setBody(event.target.value)
      }),
      jsxs('div', { style: { ...styles.controlRow, marginTop: '8px' }, children: [
        jsx('select', {
          value: tier,
          'aria-label': 'Memory tier',
          onChange: (event) => setTier(event.target.value),
          style: styles.select,
          children: ['learning', 'work', 'knowledge'].map((value) => jsx('option', { value, key: value, children: value }))
        }),
        jsx('input', {
          style: styles.input,
          value: tags,
          placeholder: 'comma,separated,tags',
          'aria-label': 'Tags',
          onChange: (event) => setTags(event.target.value)
        }),
        jsx(Button, {
          variant: 'outline',
          size: 'sm',
          disabled: busy || !title.trim() || !body.trim(),
          onClick: () => mutation.mutate({ path: '/record', body: { title: title.trim(), body: body.trim(), tier, tags: tags.trim() } }),
          children: busy ? 'Recording…' : 'Record'
        })
      ] }),
      feedback ? jsx('div', { style: { ...styles.feedback, ...(String(feedback).includes('failed') ? styles.feedbackError : {}) }, children: feedback }) : null
    ]
  })
}

function HistoryCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'action-history'], queryFn: () => api.rest('/action-history'), refetchInterval: 20000 })

  if (query.isLoading) {
    return jsx(Card, { title: 'Verification history', icon: 'history', children: jsx('div', { style: styles.unavailable, children: 'Loading recorded runs…' }) })
  }

  const entries = (query.data?.entries || []).slice().reverse()
  if (!entries.length) {
    return jsx(Card, {
      title: 'Verification history',
      icon: 'history',
      hint: query.data?.claim_boundary,
      children: jsx('div', { style: styles.unavailable, children: 'No checks have been run yet. Run one from Next checks above and it will be recorded here with its proof movement.' })
    })
  }

  // Proof delta between consecutive runs, oldest -> newest ordering in storage.
  const deltaFor = (index) => {
    const current = entries[index]
    const previous = entries[index + 1]  // reversed array: previous run sits after
    if (!previous?.proof_layers || !current?.proof_layers) return null
    const readyStates = ['inspected', 'active', 'done', 'verified', 'connected', 'ready', 'healthy', 'ok', 'source_present']
    const ready = (proof) => Object.values(proof).filter((value) => readyStates.includes(String(value).toLowerCase())).length
    return ready(current.proof_layers) - ready(previous.proof_layers)
  }

  return jsx(Card, {
    title: 'Verification history',
    icon: 'history',
    hint: `${entries.length} recorded runs · ${query.data?.claim_boundary || ''}`,
    children: jsx('div', { style: styles.routeGrid, children: entries.map((entry, index) => {
      const delta = deltaFor(index)
      const deltaColor = delta === null ? COLORS.muted : delta > 0 ? COLORS.good : delta < 0 ? COLORS.bad : COLORS.muted
      return jsxs('div', {
        style: { ...styles.routeRow },
        children: [
          jsxs('span', { style: { display: 'inline-flex', alignItems: 'center', gap: '8px', minWidth: 0 }, children: [
            jsx(StateBadge, { value: entry.status, tone: entry.ok ? undefined : 'bad' }),
            jsx('span', { style: styles.recallTitle, children: formatStatus(entry.action_id) })
          ] }),
          jsxs('span', { style: { display: 'inline-flex', alignItems: 'center', gap: '10px', flexShrink: 0 }, children: [
            delta !== null && delta !== 0 ? jsx('span', { style: { color: deltaColor, fontSize: '12px', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }, children: `${delta > 0 ? '+' : ''}${delta} layer${Math.abs(delta) === 1 ? '' : 's'}` }) : null,
            jsx('span', { style: styles.eventTime, children: formatRelativeTimestamp(entry.completed_at) })
          ] })
        ]
      }, `hist-${entry.completed_at}-${index}`)
    }) })
  })
}

function RoutesCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'routes'], queryFn: () => api.rest('/routes'), refetchInterval: 60000 })
  const [copiedName, setCopiedName] = useState(null)

  const copyFallback = (route) => {
    if (!route.fallback || !navigator.clipboard?.writeText) return
    navigator.clipboard.writeText(route.fallback).then(() => {
      setCopiedName(route.name)
      setTimeout(() => setCopiedName((current) => (current === route.name ? null : current)), 1500)
    }).catch(() => { /* clipboard unavailable — tooltip still shows the command */ })
  }

  if (query.isLoading) {
    return jsx(Card, { title: 'SIPS routes', icon: 'layout', children: jsx('div', { style: styles.unavailable, children: 'Loading declared routes…' }) })
  }

  const routes = query.data?.routes || []
  return jsx(Card, {
    title: 'SIPS routes',
    icon: 'layout',
    hint: query.data?.claim_boundary || 'Declared command surfaces; listing does not prove callability.',
    children: routes.length ? jsx('div', {
      style: styles.routeGrid,
      children: routes.map((route, index) => jsxs('div', {
        style: { ...styles.routeRow, ...(index === routes.length - 1 ? { borderBottom: 'none' } : {}) },
        children: [
          jsxs('span', { style: { display: 'inline-flex', alignItems: 'center', gap: '8px', minWidth: 0 }, children: [
            jsx('span', { style: styles.routeName, children: route.name || '?' }),
            route.fallback ? jsx('button', {
              type: 'button',
              onClick: () => copyFallback(route),
              title: route.fallback,
              'aria-label': `Copy CLI fallback for ${route.name}`,
              style: { border: `1px solid ${COLORS.border}`, borderRadius: '6px', background: 'transparent', color: copiedName === route.name ? COLORS.good : COLORS.muted, fontSize: '12px', padding: '2px 8px', cursor: navigator.clipboard ? 'pointer' : 'default', flexShrink: 0 },
              children: copiedName === route.name ? 'Copied' : 'Copy'
            }) : null
          ] }),
          jsx('span', { style: styles.routeTool, title: route.fallback || '', children: route.mcp_tool || route.fallback || '—' })
        ]
      }, `route-${route.name || index}`))
    }) : jsx('div', { style: styles.unavailable, children: 'No routes were reported.' })
  })
}

function MemoryCard({ memory }) {
  if (!memory?.available) {
    return jsx(Card, { title: 'Memory fabric', icon: 'database', children: jsx('div', { style: styles.unavailable, children: memory?.reason || 'Memory fabric is unavailable.' }) })
  }

  const records = Number(memory.record_count) || 0
  const verified = Math.min(records, Number(memory.verified_or_active_count) || 0)
  const verification = percent(verified, records)
  // Derive the semantic color from the actual percentage instead of hard-coding green.
  const memoryTone = verification >= 90 ? 'good' : verification >= 50 ? 'accent' : 'warn'
  const memoryColor = COLORS[memoryTone]

  return jsx(Card, {
    title: 'Memory fabric',
    icon: 'database',
    hint: memory.store_present ? 'Local store detected; raw records remain hidden.' : 'Store has not been created yet.',
    children: [
      jsx('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }, children: [jsx('span', { style: styles.label, children: 'Verification coverage' }), jsx('span', { style: { ...styles.value, color: memoryColor, fontVariantNumeric: 'tabular-nums' }, children: `${verification}%` })] }),
      jsx('div', { style: styles.memoryTrack, children: [
        jsx('div', { style: { ...styles.memoryVerified, width: `${verification}%`, background: memoryColor } }),
        jsx('div', { style: { ...styles.memoryOther, width: `${100 - verification}%` } })
      ] }),
      jsx('div', { style: styles.row, children: [jsx('span', { style: styles.label, children: 'Records' }), jsx('span', { style: { ...styles.value, fontVariantNumeric: 'tabular-nums' }, children: compactNumber(records) })] }),
      jsx('div', { style: styles.row, children: [jsx('span', { style: styles.label, children: 'Verified or active' }), jsx('span', { style: { ...styles.value, color: COLORS.good, fontVariantNumeric: 'tabular-nums' }, children: compactNumber(verified) })] }),
      jsx('div', { style: styles.rowLast, children: [jsx('span', { style: styles.label, children: 'Store' }), jsx(StateBadge, { value: memory.store_present ? 'connected' : 'pending' })] })
    ]
  })
}

function RuntimeCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'runtime'], queryFn: () => api.rest('/runtime'), refetchInterval: 20000 })

  if (query.isLoading) {
    return jsx(Card, { title: 'Runtime goal board', icon: 'target', children: jsx('div', { style: styles.unavailable, children: 'Reading runtime runs…' }) })
  }
  const runtime = query.data
  if (!runtime?.available) {
    return jsx(Card, {
      title: 'Runtime goal board',
      icon: 'target',
      hint: 'Backed by sips_runtime graph events.',
      children: jsx('div', { style: styles.unavailable, children: runtime?.reason || 'No runtime event stream yet — it appears once a session bridges to the graph runtime.' })
    })
  }

  const progress = runtime.progress || { complete: 0, total: 0 }
  const ratio = Math.round((Number(progress.ratio) || 0) * 100)
  const boardTone = runtime.status === 'succeeded' ? 'good' : runtime.status === 'failed' ? 'bad' : 'accent'
  const tasks = runtime.tasks || []

  return jsx(Card, {
    title: 'Runtime goal board',
    icon: 'target',
    hint: `Run ${runtime.run_id || '?'} · rev ${runtime.revision ?? '?'} · authority ${runtime.authority || 'unknown'}`,
    children: [
      jsx('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }, children: [
        jsx('span', { style: styles.label, children: runtime.objective || 'Session work' }),
        jsx(StateBadge, { value: runtime.status, tone: boardTone })
      ] }),
      jsx('div', { style: styles.memoryTrack, children: [
        jsx('div', { style: { width: `${ratio}%`, background: COLORS[boardTone] } }),
        jsx('div', { style: { ...styles.memoryOther, width: `${100 - ratio}%` } })
      ] }),
      jsx('div', { style: styles.row, children: [
        jsx('span', { style: styles.label, children: 'Task progress' }),
        jsx('span', { style: { ...styles.value, fontVariantNumeric: 'tabular-nums' }, children: `${progress.complete}/${progress.total}` })
      ] }),
      tasks.slice(0, 4).map((task) => jsxs('div', { style: styles.row, children: [
        jsx('span', { style: styles.label, children: [
          jsx(Codicon, { name: task.status === 'succeeded' ? 'check' : task.status === 'failed' ? 'error' : 'sync', size: '0.85em', style: { verticalAlign: '-0.12em', marginRight: '5px', color: COLORS[task.status === 'succeeded' ? 'good' : task.status === 'failed' ? 'bad' : 'accent'] } }),
          task.title || task.id
        ] }),
        jsx('span', { style: styles.value, children: task.has_receipt ? jsx(StateBadge, { value: task.status }) : formatStatus(task.status) })
      ] }, `rt-${task.id}`)),
      jsx('div', { style: styles.rowLast, children: [
        jsx('span', { style: styles.label, children: 'Source' }),
        jsx('span', { style: { ...styles.value, color: COLORS.muted, fontSize: '12px' }, children: runtime.source_path ? 'persisted runtime events' : 'in-memory projection' })
      ] })
    ]
  })
}

function EventsCard({ events }) {
  const [filter, setFilter] = useState('all')
  const [expanded, setExpanded] = useState(false)

  if (!events?.available || !events.recent?.length) {
    return jsx(Card, { title: 'Lifecycle stream', icon: 'pulse', children: jsx('div', { style: styles.unavailable, children: 'No lifecycle events are available yet.' }) })
  }

  const recent = events.recent.slice().reverse()
  const outcomes = ['all', ...new Set(recent.map((event) => event.outcome || 'observed'))]
  const filtered = filter === 'all' ? recent : recent.filter((event) => (event.outcome || 'observed') === filter)
  const visible = expanded ? filtered : filtered.slice(0, 6)

  return jsx(Card, {
    title: 'Lifecycle stream',
    icon: 'pulse',
    hint: `${compactNumber(events.event_count || 0)} recorded events · ${filtered.length} shown`,
    children: [
      jsx('div', {
        style: styles.eventToolbar,
        children: [
          jsx('span', { style: { ...styles.filterCount, color: COLORS.muted }, children: filter === 'all' ? 'All outcomes' : `Outcome: ${formatStatus(filter)}` }),
          jsx('select', {
            value: filter,
            'aria-label': 'Filter lifecycle outcomes',
            onChange: (event) => setFilter(event.target.value),
            style: styles.select,
            children: outcomes.map((outcome) => jsx('option', { value: outcome, children: outcome === 'all' ? 'All outcomes' : formatStatus(outcome), key: outcome }))
          })
        ]
      }),
      filtered.length ? jsx('div', { style: styles.tapeStrip, children: [
        ...visible.map((event, index) => {
          const tone = toneFor(event.outcome)

          return jsxs('div', {
            style: styles.tapeRow,
            key: `${event.timestamp || 'event'}-${index}`,
            children: [
              jsxs('span', { style: { display: 'inline-flex', alignItems: 'center', gap: '8px', minWidth: 0 }, children: [
                jsx('span', {
                  'aria-hidden': true,
                  style: { width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0, background: toneColor(event.outcome), boxShadow: `0 0 0 2px ${tone === 'good' ? 'rgba(105,211,154,0.15)' : tone === 'bad' ? 'rgba(242,139,139,0.15)' : 'rgba(125,211,252,0.15)'}` }
                }),
                jsx('span', { style: { fontWeight: 650, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: formatStatus(event.event) }),
                event.tool ? jsx('span', { style: { color: 'rgba(51,48,42,0.6)' }, children: `· ${event.tool}` }) : null
              ] }),
              jsxs('span', { style: { flexShrink: 0, color: 'rgba(51,48,42,0.6)' }, children: [
                formatStatus(event.outcome || 'observed'),
                ' — ',
                formatRelativeTimestamp(event.timestamp)
              ] })
            ]
          })
        }),
        filtered.length > 6 ? jsx('div', {
          style: { ...styles.eventToggleRow, marginTop: '10px' },
          key: 'toggle',
          children: jsx(Button, { variant: 'outline', size: 'sm', onClick: () => setExpanded((value) => !value), children: expanded ? 'Show fewer' : `Show all ${compactNumber(recent.length)} events` })
        }) : null,
        events.recent_capped ? jsx('div', {
          style: { ...styles.eventCapNote, marginTop: '8px' },
          key: 'capped',
          children: `Showing the most recent ${events.recent.length} of ${compactNumber(events.event_count || 0)} recorded events.`
        }) : null
      ], key: 'tape' }) : jsx('div', { style: styles.unavailable, children: `No lifecycle events match ${formatStatus(filter)}.` })
    ]
  })
}

const PROOF_DESCRIPTIONS = {
  repo_source: ['Repository source', 'The SIPS repository source was located and inspected.', 'This does not prove the installed desktop cache or live transport.'],
  worktree: ['Worktree', 'The local worktree was available for inspection.', 'This does not prove that the running host uses this worktree.'],
  installed_cache: ['Installed cache', 'The installed plugin/cache surface was inspected.', 'This does not prove that the host currently advertises every task.'],
  host_config: ['Host configuration', 'The Hermes/Codex host configuration was inspected.', 'This does not prove that a live task call can complete.'],
  task_advertisement: ['Task advertisement', 'The host-advertised task surface was inspected.', 'This does not prove the advertised task is callable end to end.'],
  task_callability: ['Task callability', 'A task callability probe completed successfully.', 'This does not prove every tool or route is healthy.'],
  transport: ['Transport', 'The active transport was inspected.', 'This does not prove the source or worktree is current.']
}

function proofDescription(name, value) {
  const [title, ready, boundary] = PROOF_DESCRIPTIONS[name] || [name.replaceAll('_', ' '), 'A SIPS proof layer reported a state.', 'No additional claim boundary was provided by the plugin.']
  return { title, summary: toneFor(value) === 'good' ? ready : `This layer is currently ${formatStatus(value)}.`, boundary }
}

function ProofCard({ proof, actionState }) {
  const entries = Object.entries(proof || {})

  return jsx(Card, {
    title: 'Proof layers',
    icon: 'verified',
    lead: true,
    hint: 'Click a breaker door to swing it open and see what it establishes — and where the claim boundary remains.',
    children: entries.length ? jsx('div', {
      style: { display: 'grid', gap: '9px' },
      children: entries.map(([name, value]) => {
        const description = proofDescription(name, value)
        const actionId = actionState?.proofActions?.[name]
        const action = actionState?.actions?.find((candidate) => candidate.id === actionId)
        return jsx(Breaker, {
          key: name,
          title: description.title,
          badge: jsx(StateBadge, { value }),
          summary: description.summary,
          boundary: description.boundary,
          defaultOpen: toneFor(value) === 'bad',
          action: action ? jsx(Button, { variant: 'outline', size: 'sm', style: styles.proofAction, disabled: actionState.busy, onClick: () => actionState.run(action.id), children: actionState.busy && actionState.busyId === action.id ? 'Running check…' : action.label }) : null
        })
      })
    }) : jsx('div', { style: styles.unavailable, children: 'No proof layers were reported.' })
  })
}

function SurfaceCard({ counts }) {
  const rows = [['Commands', counts?.commands], ['Agents', counts?.agents], ['Scripts', counts?.scripts], ['Hook event types', counts?.hook_events], ['MCP servers', counts?.mcp_servers], ['MCP tools', counts?.mcp_tools]]
  const max = Math.max(...rows.map(([, value]) => Number(value) || 0), 1)

  return jsx(Card, {
    title: 'SIPS surface inventory',
    icon: 'layers',
    hint: 'Declared capability footprint across the local control plane.',
    children: jsx('div', {
      style: styles.proofList,
      children: rows.map(([label, value]) => {
        const amount = Number(value) || 0
        const width = amount ? Math.max(8, Math.round((amount / max) * 100)) : 0

        return jsx('div', {
          style: styles.proofRow,
          key: label,
          children: [
            jsx('div', {
              style: styles.proofRowHeader,
              children: [jsx('span', { style: styles.label, children: label }), jsx('span', { style: { ...styles.value, fontVariantNumeric: 'tabular-nums' }, children: compactNumber(amount) })]
            }),
            jsx('div', { style: styles.miniTrack, children: jsx('div', { style: { ...styles.miniFill, width: `${width}%`, background: COLORS.accent } }) })
          ]
        })
      })
    })
  })
}

function SipsPulse({ api }) {
  const gateway = useValue(host.state.gateway)
  const query = useQuery({ queryKey: ['sips-control-plane', 'status'], queryFn: () => api.rest(API_STATUS), refetchInterval: 15000 })
  const data = query.data
  const state = data?.status || (query.isError ? 'error' : 'loading')
  // Deep-link: unresolved posture lands the operator on Verification directly.
  const targetTab = toneFor(state) === 'good' ? ROUTE : `${ROUTE}?tab=verification`

  // Event ping: one soft scale pulse when new lifecycle events arrive.
  // Cooldown 5s, quiet-hours + reduced-motion respected.
  const dotRef = useRef(null)
  const lastCountRef = useRef(null)
  useEffect(() => {
    const count = Number(data?.events?.event_count)
    if (!Number.isFinite(count)) return undefined
    const previous = lastCountRef.current
    lastCountRef.current = count
    if (previous === null || count <= previous) return undefined
    if (SIPS_REDUCED_MOTION() || !SIPS_AWAKE()) return undefined
    const now = Date.now()
    if (now - (lastCountRef.pingedAt || 0) < 5000) return undefined
    lastCountRef.pingedAt = now
    try {
      dotRef.current?.animate?.(
        [{ transform: 'scale(1)' }, { transform: 'scale(1.35)' }, { transform: 'scale(1)' }],
        { duration: 300, easing: 'ease-out' }
      )
    } catch { /* WAAPI unavailable — the dot just stays still */ }
    return undefined
  }, [data?.events?.event_count])

  return jsx(Tip, {
    label: `SIPS ${state} · gateway ${gateway}`,
    children: jsxs('button', {
      type: 'button',
      onClick: () => host.navigate(targetTab),
      style: { display: 'inline-flex', alignItems: 'center', gap: '6px', height: '100%', padding: '0 8px', border: 0, background: 'transparent', color: toneColor(state), cursor: 'pointer', fontSize: '12px' },
      children: [jsx('span', { ref: dotRef, style: { display: 'inline-flex' }, children: jsx(Codicon, { name: 'pulse', size: '0.75rem' }) }), jsx('span', { children: 'SIPS' }), jsx('span', { style: { color: COLORS.muted }, children: state })]
    })
  })
}

function Dashboard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'status'], queryFn: () => api.rest(API_STATUS), refetchInterval: 15000 })
  const data = query.data
  const counts = data?.surface_counts || {}
  const actionState = useSipsActions(api, data, query.isError)
  const selfloopQuery = useQuery({ queryKey: ['sips-control-plane', 'selfloop'], queryFn: () => api.rest('/selfloop'), refetchInterval: 30000 })
  const [history, setHistory] = useState([])

  useEffect(() => {
    if (!data) return

    const posture = postureFor(data)
    const surfaceTotal = Object.values(data.surface_counts || {}).reduce((sum, value) => sum + (Number(value) || 0), 0)
    const sample = {
      key: [data.generated_at, data.events?.event_count, data.memory?.verified_or_active_count, surfaceTotal].join('|'),
      proofCoverage: posture.coverage,
      surfaceTotal,
      memoryVerified: Number(data.memory?.verified_or_active_count) || 0,
      lifecycle: Number(data.events?.event_count) || 0
    }

    setHistory((previous) => {
      if (previous[previous.length - 1]?.key === sample.key) return previous
      return [...previous, sample].slice(-12)
    })
  }, [data])

  const updatedAt = query.dataUpdatedAt || (data?.generated_at ? new Date(data.generated_at).getTime() : undefined)
  const refreshLabel = 'Refresh'
  const manifest = data?.manifest || {}
  const capabilityChips = [
    manifest.has_hooks ? 'hooks' : null,
    manifest.has_commands ? 'commands' : null,
    manifest.has_mcp_servers ? 'mcp' : null
  ].filter(Boolean)

  // Tab state: which workspace is in focus. Recommended-check count drives a
  // badge on Verification so unresolved work stays visible from any tab.
  // Priority: ?tab= query param (statusbar deep link) > stored tab > overview.
  const recommendedCount = (data?.actions || []).filter((action) => action.recommended).length
  const proofGapCount = Object.values(data?.proof_layers || {}).filter((value) => toneFor(value) !== 'good').length
  const tabs = [
    { id: 'overview', label: 'Overview', icon: 'pulse' },
    { id: 'verification', label: 'Verification', icon: 'verified', count: recommendedCount },
    { id: 'memory', label: 'Memory', icon: 'database' },
    { id: 'activity', label: 'Activity', icon: 'history' }
  ]
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const linked = new URLSearchParams(window.location?.search || '').get('tab')
      if (linked && ['overview', 'verification', 'memory', 'activity'].includes(linked)) return linked
      return localStorage.getItem(SIPS_TAB_KEY) || 'overview'
    } catch { return 'overview' }
  })
  useEffect(() => {
    try { localStorage.setItem(SIPS_TAB_KEY, activeTab) } catch { /* private mode */ }
  }, [activeTab])

  // Workspace switch: instant state swap; the entering workspace gets a cheap
  // CSS mount animation. No View Transition — snapshotting the whole page
  // (including the atmosphere gradients) made tab switches visibly laggy.
  const switchTab = (id) => {
    setActiveTab(id)
  }

  // ⌘1-4 switches tabs, but only while focus lives inside the SIPS page so we
  // never hijack the composer's or app-shell's shortcuts.
  useEffect(() => {
    if (typeof document === 'undefined') return undefined
    const onKeyDown = (event) => {
      if (!(event.metaKey || event.ctrlKey) || event.altKey || event.shiftKey) return
      const index = ['1', '2', '3', '4'].indexOf(event.key)
      if (index === -1) return
      const withinPage = event.target instanceof Element && Boolean(event.target.closest('[data-sips-page]'))
      const focusInPage = document.activeElement instanceof Element && Boolean(document.activeElement.closest('[data-sips-page]'))
      if (!withinPage && !focusInPage) return
      const tab = tabs[index]
      if (tab) {
        event.preventDefault()
        switchTab(tab.id)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [tabs])

  if (query.isLoading) {
    return jsx('div', { style: { ...styles.page, display: 'grid', placeItems: 'center' }, children: jsx(Loader, { type: 'lemniscate-bloom' }) })
  }
  if (query.isError && !data) {
    return jsx('div', { style: styles.page, children: jsx('div', { style: styles.max, children: [jsx('div', { style: styles.eyebrow, children: 'SIPS CONTROL PLANE' }), jsx('h1', { style: styles.title, children: 'Homebase unavailable' }), jsx('p', { style: styles.subtitle, children: 'The dashboard could not read the local SIPS summary. Normal Hermes operation is unaffected; retry after the backend/plugin is available.' }), jsx(Button, { variant: 'outline', size: 'sm', onClick: () => query.refetch(), children: 'Retry' })] }) })
  }

  return jsx('div', { 'data-sips-page': true, style: styles.page, children: jsx('div', { style: styles.max, children: [
    // Ambient atmosphere layer: hue/period/alpha encode live posture — good
    // posture breathes slowly in green, partial in amber, unhealthy pulses red.
    jsx(AtmosphereLayer, { tone: postureToneOf(data), coverage: postureCoverageOf(data) }),
    jsxs('header', { style: styles.header, children: [jsx('div', { children: [jsx('div', { style: styles.eyebrow, children: 'SIPS CONTROL PLANE' }), jsx('h1', { style: styles.title, children: 'Self-improvement, made visible.' }), jsx('p', { style: styles.subtitle, children: data.claim_boundary || 'Read-only operational view of SIPS health, proof, goals, memory, and lifecycle activity.' })] }), jsx('div', { style: styles.actions, children: [jsx(Button, { variant: 'outline', size: 'sm', onClick: () => query.refetch(), children: refreshLabel })] })] }),
    query.isError ? jsx('div', { style: { ...styles.unavailable, marginBottom: '14px', borderColor: COLORS.warn }, children: 'Refresh failed; showing the last successful SIPS snapshot.' }) : null,
    jsxs('div', { style: styles.metaRow, children: [
      data.version ? jsx('span', { style: styles.metaText, children: `v${data.version}` }) : null,
      ...capabilityChips.map((chip) => jsx(Badge, { key: chip, variant: 'outline', style: styles.metaBadge, children: chip })),
      jsx('span', { style: styles.metaText, children: data.git?.is_git ? 'git repo' : 'no git' })
    ] }),
    jsx(StatusOverview, { data, history, updatedAt, isFetching: query.isFetching, fetchError: query.isError, selfloopActive: Boolean(selfloopQuery.data?.active) }),
    // Mission rail + workspace column: the raised spine carries navigation,
    // live posture beacon, and badges; content swaps to its right.
    jsxs('div', { style: styles.layout, children: [
      jsxs('nav', { style: styles.rail, role: 'tablist', 'aria-label': 'SIPS workspaces', 'aria-orientation': 'vertical', children: [
        jsxs('div', { style: styles.railHead, children: [
          jsx('span', {
            'data-sips-heartbeat': selfloopQuery.data?.active && SIPS_AWAKE() ? 'on' : 'off',
            style: { ...styles.railDot, background: toneColor(data?.status), boxShadow: `0 0 8px ${toneColor(data?.status)}` }
          }),
          jsx('span', { style: styles.tabBarLabel, children: 'Workspaces' })
        ] }),
        jsx('div', { style: styles.railItems, children: tabs.map((tab) => jsxs('button', {
          type: 'button',
          role: 'tab',
          'aria-selected': activeTab === tab.id,
          'data-sips-railitem': activeTab === tab.id ? 'active' : true,
          onClick: () => switchTab(tab.id),
          style: styles.railItem,
          key: tab.id,
          children: [
            activeTab === tab.id ? jsx('span', { style: styles.railItemMark, 'aria-hidden': true }) : null,
            jsx(Codicon, { name: tab.icon, size: '0.9rem' }),
            tab.label,
            tab.count ? jsx('span', { style: styles.tabCount, children: tab.count }) : null
          ]
        }, `tab-${tab.id}`)) })
      ] }),
      jsxs('div', { style: styles.workspace, 'data-sips-workspace': true, key: activeTab, children: [
      // Lead/support structure per workspace: the reason-for-visit leads;
      // supporting cards subordinate below. Squint test: one lead per tab.
      activeTab === 'overview' ? jsxs('div', { children: [
        jsx('div', { style: styles.leadRow, children: jsx(GoalCard, { goal: data.goal, api, selfloop: selfloopQuery.data, onSelfloopMutated: () => selfloopQuery.refetch() }) }),
        jsx('div', { style: styles.supportGrid, children: [
          jsx(RuntimeCard, { api }),
          jsx(MemoryCard, { memory: data.memory }),
          jsx(SurfaceCard, { counts })
        ] })
      ] }) : null,
      activeTab === 'verification' ? jsxs('div', { children: [
        jsx('div', { style: styles.leadRow, children: jsx(ActionCenter, { actionState }) }),
        jsx('div', { style: styles.supportGrid, children: [
          jsx(HistoryCard, { api }),
          jsx(ProofCard, { proof: data.proof_layers, actionState }),
          jsx(RoutesCard, { api })
        ] })
      ] }) : null,
      activeTab === 'memory' ? jsxs('div', { style: styles.supportGrid, children: [
        jsx(RecallCard, { api }),
        jsx(RecordCard, { api })
      ] }) : null,
      activeTab === 'activity' ? jsx(EventsCard, { events: data.events }) : null
      ] })
    ] })
  ] }) })
}

export default {
  id: 'harness-self-improvement',
  name: 'SIPS Control Plane',
  defaultEnabled: true,
  register(ctx) {
    const api = { rest: ctx.rest }
    // Keyboard focus visibility: inline styles cannot express :focus-visible, so a
    // one-time stylesheet scopes an outline to interactive elements on this page.
    if (typeof document !== 'undefined' && !document.getElementById('sips-focus-style')) {
      const styleTag = document.createElement('style')
      styleTag.id = 'sips-focus-style'
      styleTag.textContent = [
        `[data-sips-page] button:focus-visible, [data-sips-page] select:focus-visible, [data-sips-page] summary:focus-visible, [data-sips-page] a:focus-visible { outline: 2px solid ${COLORS.accent}; outline-offset: 2px; border-radius: 6px; }`,
        `@property --sips-orb { syntax: '<percentage>'; inherits: false; initial-value: 0%; }`,
        // Depth pass: resting cards lift on hover; lead cards lift further.
        `[data-sips-card] { transition: transform 180ms cubic-bezier(0.2,0.7,0.3,1), box-shadow 180ms cubic-bezier(0.2,0.7,0.3,1), border-color 180ms ease; }`,
        `[data-sips-card]:hover { transform: translateY(-2px); border-top-color: rgba(255,255,255,0.22); box-shadow: 0 2px 4px rgba(0,0,0,0.20), 0 12px 28px rgba(0,0,0,0.20); }`,
        `[data-sips-lead]:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.24), 0 22px 48px rgba(0,0,0,0.30); }`,
        `[data-sips-lead] { transition: transform 200ms cubic-bezier(0.2,0.7,0.3,1), box-shadow 200ms cubic-bezier(0.2,0.7,0.3,1); }`,
        // Recessed wells: inputs/selects/textareas sit below the card plane.
        `[data-sips-page] input, [data-sips-page] select, [data-sips-page] textarea { box-shadow: inset 0 1px 3px rgba(0,0,0,0.30); }`,
        `[data-sips-page] details > div { box-shadow: inset 0 1px 3px rgba(0,0,0,0.22); }`,
        // Ambient atmosphere layer: posture hue + breathing rate are set from JS
        // via CSS custom properties on the wrapper. No filter blur — the radial
        // gradients are already soft, and blur is a per-frame GPU cost.
        `[data-sips-atmosphere] { position: absolute; inset: -80px 0 auto 0; height: 480px; pointer-events: none; z-index: 0; opacity: var(--sips-atmo-alpha, 0.55); transform: translateZ(0); will-change: opacity; }`,
        `[data-sips-atmosphere]::before { content: ''; position: absolute; inset: 0; background: radial-gradient(560px 300px at 72% 18%, var(--sips-atmo-hue, rgba(105,211,154,0.16)), transparent 70%); animation: sips-breathe var(--sips-atmo-period, 9s) ease-in-out infinite; }`,
        `[data-sips-atmosphere]::after { content: ''; position: absolute; inset: 0; background: radial-gradient(420px 240px at 18% 42%, var(--sips-atmo-hue-soft, rgba(125,211,252,0.10)), transparent 70%); animation: sips-breathe calc(var(--sips-atmo-period, 9s) * 1.6) ease-in-out infinite reverse; }`,
        `[data-sips-heartbeat] { animation: sips-breathe 4s ease-in-out infinite; animation-play-state: paused; }`,
        `[data-sips-heartbeat="on"] { animation-play-state: running; }`,
        `@keyframes sips-breathe { 0%, 100% { opacity: 0.25; } 50% { opacity: 0.5; } }`,
        // Selfloop shimmer: a faint conic highlight orbiting the hero edge while
        // the self-improvement loop runs. Purely decorative, evidence-gated by
        // the data attribute set from live selfloop state.
        `[data-sips-selfloop] { position: relative; overflow: hidden; }`,
        `[data-sips-selfloop="on"]::before { content: ''; position: absolute; inset: -60%; background: conic-gradient(from var(--sips-spin, 0deg), transparent 0deg, rgba(125,211,252,0.05) 40deg, rgba(105,211,154,0.07) 70deg, transparent 110deg); z-index: 0; pointer-events: none; animation: sips-orbit 26s linear infinite; }`,
        `@keyframes sips-orbit { to { transform: rotate(360deg); } }`,
        // Mission rail states.
        `[data-sips-railitem] { transition: background 130ms ease, color 130ms ease; }`,
        `[data-sips-railitem]:hover { background: rgba(255,255,255,0.055); color: ${COLORS.text}; }`,
        `[data-sips-railitem="active"] { background: rgba(255,255,255,0.07); color: ${COLORS.text}; box-shadow: inset 0 1px 0 rgba(255,255,255,0.07); }`,
        // Instrument press: the push button's cap sinks into its recess.
        `[data-sips-push] { transition: transform 90ms ease, box-shadow 90ms ease; }`,
        `[data-sips-push]:not(:disabled):active { transform: translateY(1px); box-shadow: inset 0 4px 9px rgba(0,0,0,0.8), inset 0 1px 2px rgba(0,0,0,0.6); }`,
        `[data-sips-push]:not(:disabled):active span { transform: translateY(1px); }
        [data-sips-push] span { transition: transform 90ms ease; }`,
        // Workspace mount: cheap opacity/translate on the entering content only —
        // no full-page View Transition snapshot.
        `[data-sips-workspace] { animation: sips-mount 170ms cubic-bezier(0.2,0.7,0.3,1) both; }`,
        `@keyframes sips-mount { from { opacity: 0; transform: translateY(7px); } to { opacity: 1; transform: none; } }`,
        `::view-transition-old(root) { animation: sips-vt-out 120ms ease-in both; }`,
        `::view-transition-new(root) { animation: sips-vt-in 160ms ease-out both; }`,
        `@keyframes sips-vt-out { to { opacity: 0; } }`,
        `@keyframes sips-vt-in { from { opacity: 0; transform: translateY(8px); } }`,
        `@media (prefers-reduced-motion: reduce) { [data-sips-heartbeat] { animation: none !important; } ::view-transition-old(root), ::view-transition-new(root) { animation: none !important; } [data-sips-card], [data-sips-lead] { transition: none !important; } [data-sips-card]:hover, [data-sips-lead]:hover { transform: none !important; } [data-sips-atmosphere]::before, [data-sips-atmosphere]::after, [data-sips-selfloop="on"]::before, [data-sips-workspace] { animation: none !important; } [data-sips-railitem], [data-sips-push], [data-sips-push] span { transition: none !important; } }`,
        // Dial needle + toggle knob snap instead of sweeping under reduced motion.
        `@media (prefers-reduced-motion: reduce) { [style*="dial-needle"], .sips-dial-needle, .sips-toggle-knob { transition: none !important; } }`
      ].join('\n')
      document.head.appendChild(styleTag)
    }
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, title: 'SIPS Control Plane', data: { path: ROUTE }, render: () => jsx(Dashboard, { api }) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, order: 60, data: { codicon: 'pulse', label: 'SIPS', path: ROUTE } },
      { id: 'pulse', area: STATUSBAR_AREAS.right, order: 90, render: () => jsx(SipsPulse, { api }) }
    ])
  }
}
