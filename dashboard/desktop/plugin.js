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
  // --- THE BOARD palette -----------------------------------------------------
  // Matte flap faces, steel chassis, letter white. Exactly two semantic hues
  // (amber = attention/delay, red = failure) plus a live green reserved for
  // lamps only. No decorative accent: amber is the active/attention color.
  ink: '#0b0d10',
  flap: '#0d0e11',
  flapRaised: '#131519',
  chassis: '#16181d',
  chassisDeep: '#101215',
  seam: 'rgba(255,255,255,0.055)',
  frame: '#2c3037',
  frameLight: '#43484f',
  steel: '#9aa1ab',
  steelDim: '#79808b',
  letter: '#f2f2f2',
  amber: '#ffb000',
  amberDim: 'rgba(255,176,0,0.14)',
  red: '#ff5a5a',
  redDim: 'rgba(255,90,90,0.14)',
  green: '#39d98a',
  greenDim: 'rgba(57,217,138,0.16)',
  // Kept for host-token fallbacks inside shared SDK components.
  text: '#f2f2f2',
  muted: '#8b919b',
  border: '#2c3037',
  panel: '#16181d',
  accent: '#ffb000',
  good: '#39d98a',
  warn: '#ffb000',
  bad: '#ff5a5a'
}

const TONE_LAMP = { good: COLORS.green, warn: COLORS.amber, bad: COLORS.red, accent: COLORS.amber, muted: COLORS.steelDim }

const MONO = 'ui-monospace, "SF Mono", SFMono-Regular, Menlo, monospace'
const COND = '"SF Pro Display", "SF Pro Text", -apple-system, "Segoe UI", system-ui, sans-serif'

const styles = {
  page: {
    boxSizing: 'border-box',
    position: 'relative',
    height: '100%',
    overflow: 'auto',
    padding: '24px 30px 56px',
    color: COLORS.letter,
    background: 'radial-gradient(1100px 420px at 50% -160px, #171a20, transparent 70%), linear-gradient(180deg, #101215, #0b0d10 320px)',
    fontFamily: COND
  },
  max: { maxWidth: '1240px', margin: '0 auto', position: 'relative', zIndex: 1 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '20px', marginBottom: '18px' },
  eyebrow: { color: COLORS.amber, fontSize: '11px', fontWeight: 700, letterSpacing: '0.22em', textTransform: 'uppercase', fontFamily: MONO },
  title: { fontSize: '26px', lineHeight: 1.1, fontWeight: 800, margin: '7px 0 7px', textTransform: 'uppercase', letterSpacing: '0.01em' },
  subtitle: { color: COLORS.steel, fontSize: '12.5px', lineHeight: 1.55, maxWidth: '700px' },
  actions: { display: 'flex', gap: '8px', alignItems: 'center', flexShrink: 0 },
  sectionGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '14px', alignItems: 'start' },
  // Steel panel: the board chassis. Subtle top-light, machined edge, corner
  // rivets come from the Card component's plate.
  card: {
    background: 'linear-gradient(180deg, #191c21, #131519 62%)',
    border: '1px solid #23262c',
    borderTopColor: '#34383f',
    borderRadius: '10px',
    padding: '15px 16px 14px',
    marginBottom: '14px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.5), 0 10px 26px rgba(0,0,0,0.35)'
  },
  cardTitle: { display: 'flex', alignItems: 'center', gap: '9px', fontWeight: 750, fontSize: '13px', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.09em' },
  cardHint: { color: COLORS.steelDim, fontSize: '11.5px', margin: '-7px 0 12px', lineHeight: 1.5 },
  // Board row: ruled row on the flap field. Fixed rhythm, hairline separators.
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', padding: '7px 8px', borderBottom: `1px solid ${COLORS.seam}`, background: COLORS.flap, borderRadius: '4px', marginBottom: '3px' },
  rowLast: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', padding: '7px 8px', background: COLORS.flap, borderRadius: '4px' },
  label: { color: COLORS.steelDim, fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 650 },
  value: { fontSize: '12px', fontWeight: 650, textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: COLORS.letter },
  objective: { fontSize: '14.5px', lineHeight: 1.45, fontWeight: 650, margin: '2px 0 14px', color: COLORS.letter },
  progressTrack: { height: '10px', background: COLORS.flap, border: `1px solid ${COLORS.seam}`, borderRadius: '3px', overflow: 'hidden', margin: '8px 0 7px', display: 'flex' },
  progressFill: { height: '100%', background: COLORS.amber, borderRadius: 0, transition: 'width 420ms cubic-bezier(0.2, 0.7, 0.3, 1)' },
  proof: { padding: '10px 11px', border: `1px solid ${COLORS.seam}`, borderRadius: '6px', background: COLORS.flap },
  proofName: { color: COLORS.steelDim, fontSize: '11px', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.09em' },
  proofList: { display: 'grid', gap: '10px' },
  proofRow: { display: 'grid', gap: '6px' },
  proofRowHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' },
  miniTrack: { height: '5px', background: COLORS.flap, border: `1px solid ${COLORS.seam}`, borderRadius: '2px', overflow: 'hidden' },
  miniFill: { height: '100%', borderRadius: 0, transition: 'width 420ms cubic-bezier(0.2, 0.7, 0.3, 1)', background: COLORS.amber },
  hero: {
    position: 'relative', overflow: 'hidden', padding: '18px 20px 16px', marginBottom: '14px',
    background: 'linear-gradient(180deg, #1b1e24, #121419 70%)',
    border: '1px solid #23262c', borderTopColor: '#3a3f47', borderRadius: '10px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.55), 0 18px 40px rgba(0,0,0,0.4)'
  },
  heroGlow: { display: 'none' },
  heroLayout: { position: 'relative', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '24px' },
  heroIdentity: { minWidth: 0 },
  heroTitle: { fontSize: '20px', lineHeight: 1.15, fontWeight: 800, margin: '5px 0 7px', textWrap: 'balance', textTransform: 'uppercase', letterSpacing: '0.01em' },
  heroText: { color: COLORS.steel, fontSize: '12.5px', lineHeight: 1.55, maxWidth: '650px', textWrap: 'pretty' },
  heroFooter: { display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginTop: '13px' },
  updated: { color: COLORS.steel, fontSize: '11.5px', fontVariantNumeric: 'tabular-nums', fontFamily: MONO },
  readiness: { display: 'grid', justifyItems: 'center', gap: '6px', flexShrink: 0 },
  readinessOrb: { width: '86px', height: '86px', display: 'grid', placeItems: 'center', borderRadius: '50%', background: 'conic-gradient(var(--sips-orb-color, #39d98a) var(--sips-orb, 0%), #0d0e11 0)', border: '1px solid #2c3037', boxShadow: 'inset 0 2px 6px rgba(0,0,0,0.6)' },
  readinessOrbInner: { width: '68px', height: '68px', display: 'grid', placeItems: 'center', borderRadius: '50%', background: 'radial-gradient(circle at 40% 32%, #1d2026, #0d0e11 74%)', border: '1px solid #23262c', textAlign: 'center' },
  readinessValue: { fontSize: '17px', lineHeight: 1, fontWeight: 800, fontVariantNumeric: 'tabular-nums', color: COLORS.letter },
  readinessLabel: { color: COLORS.steelDim, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.12em', textAlign: 'center' },
  signalGrid: { position: 'relative', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(165px, 1fr))', gap: '8px', marginTop: '16px' },
  // Signal = flap counter cell: ink face, seam, tabular digits.
  signal: { minWidth: 0, padding: '9px 11px 10px', border: `1px solid ${COLORS.seam}`, borderRadius: '5px', background: COLORS.flap, position: 'relative', overflow: 'hidden' },
  signalLabel: { color: COLORS.steelDim, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.13em', fontWeight: 700 },
  signalValue: { fontSize: '18px', fontWeight: 800, marginTop: '5px', fontVariantNumeric: 'tabular-nums', color: COLORS.letter, fontFamily: MONO },
  signalDetail: { color: COLORS.steelDim, fontSize: '11px', marginTop: '3px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  signalTrack: { height: '4px', marginTop: '8px', background: '#08090b', border: `1px solid ${COLORS.seam}`, borderRadius: '2px', overflow: 'hidden' },
  sparkline: { display: 'block', width: '100%', height: '23px', marginTop: '7px', overflow: 'visible' },
  freshness: { display: 'inline-flex', alignItems: 'center', gap: '6px', color: COLORS.steel, fontSize: '11.5px', fontVariantNumeric: 'tabular-nums', fontFamily: MONO },
  freshnessDot: { width: '6px', height: '6px', borderRadius: '50%', background: COLORS.green },
  proofDetail: { marginTop: '7px', padding: '9px 10px', borderRadius: '5px', background: '#0b0c0f', color: COLORS.steel, fontSize: '11.5px', lineHeight: 1.5, border: `1px solid ${COLORS.seam}` },
  proofSummary: { cursor: 'pointer', listStyle: 'none' },
  eventToolbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '4px' },
  select: { minHeight: '30px', padding: '0 26px 0 9px', border: `1px solid ${COLORS.frame}`, borderRadius: '4px', background: COLORS.flap, color: COLORS.letter, fontSize: '11.5px', fontFamily: MONO },
  filterCount: { color: COLORS.steelDim, fontSize: '11.5px', fontVariantNumeric: 'tabular-nums' },
  actionGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '8px' },
  action: { display: 'grid', gap: '8px', padding: '11px', border: `1px solid ${COLORS.seam}`, borderRadius: '6px', background: COLORS.flap },
  actionTitle: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' },
  actionDescription: { color: COLORS.steel, fontSize: '11.5px', lineHeight: 1.5 },
  actionButton: { minHeight: '40px', justifySelf: 'start' },
  actionResult: { marginTop: '10px', padding: '10px', borderRadius: '5px', border: `1px solid ${COLORS.seam}`, background: '#0b0c0f', color: COLORS.steel, fontSize: '11.5px', lineHeight: 1.5 },
  actionResultError: { borderColor: COLORS.red, color: COLORS.red },
  proofAction: { minHeight: '36px', marginTop: '9px' },
  event: { position: 'relative', display: 'grid', gridTemplateColumns: '10px minmax(0, 1fr)', gap: '10px', padding: '8px 0 8px 1px', borderBottom: `1px solid ${COLORS.seam}` },
  eventRail: { position: 'absolute', left: '4px', top: '18px', bottom: '-10px', width: '1px', background: COLORS.frame },
  eventDot: { position: 'relative', zIndex: 1, width: '7px', height: '7px', borderRadius: '50%', background: COLORS.amber, marginTop: '5px', boxShadow: '0 0 6px rgba(255,176,0,0.35)' },
  eventBody: { minWidth: 0 },
  eventTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' },
  eventName: { fontSize: '11.5px', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: MONO },
  eventTime: { color: COLORS.steelDim, fontSize: '11px', flexShrink: 0, fontVariantNumeric: 'tabular-nums', fontFamily: MONO },
  eventMeta: { color: COLORS.steelDim, fontSize: '11px', marginTop: '3px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  memoryTrack: { height: '8px', display: 'flex', gap: '2px', margin: '5px 0 10px', background: COLORS.flap, border: `1px solid ${COLORS.seam}`, borderRadius: '2px', overflow: 'hidden' },
  memoryVerified: { height: '100%', background: COLORS.amber },
  memoryOther: { height: '100%', background: 'rgba(139,145,155,0.22)' },
  empty: { border: `1px dashed ${COLORS.frame}`, borderRadius: '6px', color: COLORS.steel, padding: '15px', fontSize: '11.5px', lineHeight: 1.55, background: COLORS.flap },
  unavailable: { border: `1px dashed ${COLORS.frame}`, borderRadius: '6px', color: COLORS.steel, padding: '15px', fontSize: '11.5px', lineHeight: 1.55, background: COLORS.flap },
  metaRow: { display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '14px', color: COLORS.steelDim, fontSize: '11.5px' },
  metaText: { color: COLORS.steelDim, fontSize: '11px', fontVariantNumeric: 'tabular-nums', fontFamily: MONO, textTransform: 'uppercase', letterSpacing: '0.08em' },
  metaBadge: { fontSize: '10.5px', padding: '1px 7px', fontFamily: MONO, textTransform: 'uppercase', letterSpacing: '0.08em' },
  controlRow: { display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' },
  input: { flex: '1 1 160px', minWidth: '140px', minHeight: '32px', padding: '0 10px', border: `1px solid ${COLORS.frame}`, borderRadius: '4px', background: '#0b0c0f', color: COLORS.letter, fontSize: '12px', boxSizing: 'border-box', fontFamily: MONO },
  textarea: { width: '100%', minHeight: '58px', padding: '8px 10px', border: `1px solid ${COLORS.frame}`, borderRadius: '4px', background: '#0b0c0f', color: COLORS.letter, fontSize: '12px', lineHeight: 1.45, resize: 'vertical', boxSizing: 'border-box', fontFamily: MONO },
  recallResult: { display: 'grid', gap: '4px', padding: '10px 11px', marginTop: '8px', border: `1px solid ${COLORS.seam}`, borderRadius: '5px', background: '#0b0c0f' },
  recallTitle: { fontSize: '12px', fontWeight: 700, color: COLORS.letter },
  recallBody: { color: COLORS.steel, fontSize: '11.5px', lineHeight: 1.5 },
  recallTags: { display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '2px' },
  routeGrid: { display: 'grid', gap: '3px' },
  routeRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px', padding: '6px 8px', borderBottom: `1px solid ${COLORS.seam}`, background: COLORS.flap, borderRadius: '3px' },
  routeName: { fontSize: '11.5px', fontWeight: 650, fontFamily: MONO, color: COLORS.letter },
  routeTool: { color: COLORS.steelDim, fontSize: '11px', textAlign: 'right', fontFamily: MONO },
  feedback: { marginTop: '9px', padding: '9px 10px', borderRadius: '5px', border: `1px solid ${COLORS.seam}`, background: '#0b0c0f', color: COLORS.steel, fontSize: '11.5px', lineHeight: 1.5 },
  feedbackError: { borderColor: COLORS.red, color: COLORS.red },
  fleetComposer: { display: 'grid', gap: '8px', alignItems: 'start', padding: '10px 11px', border: `1px solid ${COLORS.seam}`, borderRadius: '5px', background: '#0b0c0f' },
  // Platform rail: steel column with flap-tile tabs; the active tab is lit.
  tabBar: { position: 'sticky', top: '0', zIndex: 10, display: 'flex', gap: '20px', margin: '0 -30px 20px', padding: '10px 30px 0', borderBottom: `1px solid ${COLORS.frame}`, background: 'linear-gradient(180deg, #12141a, #0e1014)' },
  tabBarLabel: { alignSelf: 'center', marginRight: '8px', color: COLORS.amber, fontSize: '10.5px', fontWeight: 800, letterSpacing: '0.2em', textTransform: 'uppercase', fontFamily: MONO },
  tab: { position: 'relative', display: 'inline-flex', alignItems: 'center', gap: '7px', minHeight: '40px', padding: '0 2px', border: 0, background: 'transparent', color: COLORS.steelDim, fontSize: '12px', fontWeight: 750, letterSpacing: '0.08em', textTransform: 'uppercase', cursor: 'pointer', fontFamily: COND, transition: 'color 150ms ease' },
  tabActive: { color: COLORS.letter },
  tabActiveMark: { position: 'absolute', left: 0, right: 0, bottom: '-1px', height: '2px', background: COLORS.amber, borderRadius: 0 },
  tabCount: { minWidth: '17px', padding: '1px 6px', textAlign: 'center', fontSize: '10.5px', borderRadius: '2px', background: COLORS.amber, color: '#131313', fontWeight: 800, fontVariantNumeric: 'tabular-nums', fontFamily: MONO },
  tabGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '14px', alignItems: 'start' },
  leadRow: { marginBottom: '14px' },
  supportGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '14px', alignItems: 'start' },
  moreChecks: { marginTop: '10px', border: `1px solid ${COLORS.seam}`, borderRadius: '5px', background: COLORS.flap, padding: '9px 11px' },
  moreChecksSummary: { cursor: 'pointer', listStyle: 'none', color: COLORS.steelDim, fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.09em' },
  moreChecksGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '8px', margin: '10px 0 2px' },
  actionButtonRow: { display: 'flex', gap: '8px', justifySelf: 'start' },
  eventToggleRow: { display: 'flex', justifyContent: 'center', marginTop: '10px' },
  eventCapNote: { color: COLORS.steelDim, fontSize: '11px', textAlign: 'center', marginTop: '8px' },
  findingsMore: { marginTop: '5px' },
  findingsMoreSummary: { cursor: 'pointer', listStyle: 'none', color: COLORS.amber },
  // Depth system: the board is physical — resting panels sit IN the chassis,
  // leads project slightly. Keep the keys (callers reference them).
  cardElevated: {
    background: 'linear-gradient(180deg, #1b1e24, #14161b 62%)',
    border: '1px solid #262a30',
    borderTopColor: '#3a3f47',
    boxShadow: '0 1px 2px rgba(0,0,0,0.5), 0 12px 28px rgba(0,0,0,0.4)'
  },
  cardLead: {
    background: 'linear-gradient(180deg, #1e222a, #15181d 60%)',
    border: '1px solid #2b2f36',
    borderTopColor: '#43484f',
    boxShadow: '0 2px 4px rgba(0,0,0,0.55), 0 18px 42px rgba(0,0,0,0.45)'
  },
  hoverLift: {
    transition: 'transform 160ms cubic-bezier(0.2, 0.7, 0.3, 1), box-shadow 160ms cubic-bezier(0.2, 0.7, 0.3, 1), border-color 160ms ease'
  },
  wellInset: { boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.45)' },
  // Mission rail: the platform column.
  layout: { display: 'grid', gridTemplateColumns: '196px minmax(0, 1fr)', gap: '18px', alignItems: 'start' },
  rail: {
    position: 'sticky',
    top: '14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    padding: '13px 11px 11px',
    background: 'linear-gradient(180deg, #1a1d23, #121419)',
    border: '1px solid #23262c',
    borderTopColor: '#34383f',
    borderRadius: '10px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.5), 0 12px 30px rgba(0,0,0,0.4)'
  },
  railHead: { display: 'flex', alignItems: 'center', gap: '8px', padding: '2px 6px 11px', borderBottom: `1px solid ${COLORS.seam}` },
  railDot: { width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0 },
  railItems: { display: 'grid', gap: '4px' },
  railItem: {
    position: 'relative',
    display: 'grid',
    gridTemplateColumns: '17px minmax(0, 1fr) auto',
    alignItems: 'center',
    gap: '9px',
    minHeight: '38px',
    padding: '0 9px 0 13px',
    border: `1px solid transparent`,
    borderRadius: '4px',
    background: 'transparent',
    color: COLORS.steelDim,
    fontSize: '12px',
    fontWeight: 700,
    letterSpacing: '0.07em',
    textTransform: 'uppercase',
    textAlign: 'left',
    cursor: 'pointer',
    fontFamily: COND
  },
  railItemMark: { position: 'absolute', left: '4px', top: '22%', bottom: '22%', width: '3px', borderRadius: '1px', background: COLORS.amber, boxShadow: '0 0 7px rgba(255,176,0,0.5)' },
  workspace: { minWidth: 0 },
  // Instrument bank: machined steel panels. Light from above, dark seams.
  module: {
    position: 'relative',
    background: 'linear-gradient(180deg, #1b1e24, #14161b 62%)',
    border: '1px solid #23262c',
    borderTopColor: '#3a3f47',
    borderRadius: '10px',
    padding: '15px 16px 14px',
    boxShadow: '0 2px 3px rgba(0,0,0,0.5), 0 10px 26px rgba(0,0,0,0.38), inset 0 1px 0 rgba(255,255,255,0.05)'
  },
  moduleLead: {
    background: 'linear-gradient(180deg, #1e222a, #15181d 60%)',
    boxShadow: '0 3px 5px rgba(0,0,0,0.55), 0 16px 40px rgba(0,0,0,0.44), inset 0 1px 0 rgba(255,255,255,0.06)'
  },
  screwPlate: { position: 'absolute', top: '7px', right: '9px', display: 'flex', gap: '6px', zIndex: 3 },
  screw: {
    width: '7px', height: '7px', borderRadius: '50%',
    background: 'radial-gradient(circle at 35% 30%, #4d525a, #17191d 74%)',
    boxShadow: 'inset 0 1px 1px rgba(255,255,255,0.22), inset 0 -1px 1px rgba(0,0,0,0.65), 0 1px 1px rgba(0,0,0,0.6)'
  },
  gaugeWrap: { position: 'relative', width: '96px', height: '96px', flexShrink: 0 },
  dialFace: {
    position: 'absolute', inset: 0, borderRadius: '50%',
    background: 'radial-gradient(circle at 42% 34%, #1d2026, #0d0e11 74%)',
    border: '1px solid #2c3037',
    boxShadow: 'inset 0 2px 5px rgba(0,0,0,0.6)'
  },
  dialTicks: { position: 'absolute', inset: 0, borderRadius: '50%' },
  dialNeedle: {
    position: 'absolute', left: '50%', bottom: '50%',
    width: '2px', height: '40%', marginLeft: '-1px',
    background: `linear-gradient(180deg, ${COLORS.amber}, rgba(255,176,0,0.2))`,
    transformOrigin: 'bottom center',
    transition: 'transform 650ms cubic-bezier(0.16, 1, 0.3, 1)'
  },
  dialHub: {
    position: 'absolute', left: '50%', bottom: '50%', width: '10px', height: '10px', marginLeft: '-5px', marginBottom: '-5px',
    borderRadius: '50%', background: 'radial-gradient(circle at 38% 32%, #4d525a, #17191d)',
    boxShadow: '0 1px 2px rgba(0,0,0,0.7)'
  },
  dialNeedleClass: 'sips-dial-needle',
  dialLabel: { textAlign: 'center', color: COLORS.steelDim, fontSize: '10px', marginTop: '6px', textTransform: 'uppercase', letterSpacing: '0.12em', fontWeight: 700 },
  // Toggle switch: steel slot, lit when on.
  toggleSlot: {
    position: 'relative', width: '52px', height: '26px', borderRadius: '999px',
    background: '#08090b',
    border: `1px solid ${COLORS.frame}`,
    boxShadow: 'inset 0 2px 5px rgba(0,0,0,0.7)',
    cursor: 'pointer', flexShrink: 0
  },
  toggleKnob: {
    position: 'absolute', top: '2px', left: '2px', width: '22px', height: '20px', borderRadius: '999px',
    background: 'linear-gradient(180deg, #565c66, #2b2f37 62%)',
    border: '1px solid rgba(0,0,0,0.55)',
    boxShadow: '0 2px 3px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.2)',
    transition: 'transform 150ms cubic-bezier(0.16, 1, 0.3, 1)'
  },
  toggleKnobClass: 'sips-toggle-knob',
  toggleOn: { transform: 'translateX(26px)' },
  // Push button: recessed steel with lit cap when running.
  pushBtn: {
    appearance: 'none', border: `1px solid ${COLORS.frame}`, padding: '9px 14px', cursor: 'pointer',
    display: 'inline-grid', placeItems: 'center', gap: '4px',
    minHeight: '52px', borderRadius: '6px',
    background: 'linear-gradient(180deg, #17191e, #101215)',
    boxShadow: 'inset 0 3px 7px rgba(0,0,0,0.75), inset 0 -1px 0 rgba(255,255,255,0.04)',
    color: COLORS.steel, fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.09em', fontFamily: COND,
    transition: 'box-shadow 90ms ease, transform 90ms ease, color 90ms ease'
  },
  pushCap: {
    display: 'grid', placeItems: 'center',
    width: '24px', height: '24px', borderRadius: '50%',
    background: 'linear-gradient(180deg, #565c66, #262a31)',
    border: '1px solid rgba(0,0,0,0.55)',
    boxShadow: '0 2px 3px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.18)'
  },
  // Inspection hatch (proof layers): steel door over a dark interior.
  breaker: { perspective: '900px', borderRadius: '6px' },
  breakerFrame: {
    position: 'relative', borderRadius: '6px', overflow: 'hidden',
    background: '#0b0c0f',
    border: `1px solid ${COLORS.seam}`,
    boxShadow: 'inset 0 2px 5px rgba(0,0,0,0.55)'
  },
  breakerDoor: {
    position: 'relative', zIndex: 2, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px',
    padding: '11px 12px',
    background: 'linear-gradient(180deg, #262a31, #1a1d23)',
    border: '1px solid #2c3037', borderTopColor: '#3d4148',
    borderRadius: '6px', transformOrigin: 'top center',
    transition: 'transform 280ms cubic-bezier(0.55, 0, 0.7, 0.35), box-shadow 280ms ease',
    boxShadow: '0 3px 5px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08)'
  },
  breakerOpen: { transform: 'rotateX(-78deg)', boxShadow: '0 -1px 3px rgba(0,0,0,0.3)' },
  breakerInterior: {
    position: 'absolute', inset: 0, zIndex: 1, padding: '11px 12px', paddingTop: '44px',
    background: '#0b0c0f', color: COLORS.steel, fontSize: '11.5px', lineHeight: 1.5
  },
  // Paper tape: receipt stub — literal SIPS receipts on ticket paper.
  tapeStrip: {
    background: 'repeating-linear-gradient(180deg, #f2ede2, #f2ede2 25px, #e9e3d6 26px)',
    color: '#2e2b26', borderRadius: '4px', padding: '12px 14px',
    boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.16), 0 3px 8px rgba(0,0,0,0.4)',
    fontVariantNumeric: 'tabular-nums', fontFamily: MONO, fontSize: '11.5px'
  },
  tapeRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px',
    padding: '4px 0', borderBottom: '1px dashed rgba(46,43,38,0.3)', fontSize: '11.5px'
  },
  // Departure rows (runs/fleet): fixed board columns.
  listRow: { display: 'grid', gap: '3px', padding: '6px 8px', borderBottom: `1px solid ${COLORS.seam}`, background: COLORS.flap, borderRadius: '3px', marginBottom: '3px' },
  listMain: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', minWidth: 0 },
  listId: { fontSize: '11.5px', fontWeight: 650, fontFamily: MONO, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0, color: COLORS.letter },
  listMeta: { display: 'inline-flex', alignItems: 'center', gap: '9px', flexShrink: 0, fontVariantNumeric: 'tabular-nums', fontFamily: MONO, fontSize: '11px', color: COLORS.steel },
  listSecondary: { color: COLORS.steelDim, fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  listTags: { display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' },
  drillRow: { display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, padding: '2px 6px', margin: '-2px -6px', borderRadius: '4px', cursor: 'pointer', textAlign: 'left' },
  drillBody: { display: 'grid', gap: '3px', minWidth: 0, flex: 1 },
  drillChevron: { display: 'inline-flex', alignItems: 'center', color: COLORS.steelDim, flexShrink: 0, transition: 'transform 150ms ease' },
  drillPanel: { margin: '4px 0 6px', padding: '10px 11px', border: `1px solid ${COLORS.seam}`, borderRadius: '5px', background: '#0b0c0f', display: 'grid', gap: '9px' },
  drillStack: { display: 'grid', gap: '9px', minWidth: 0 },
  drillHead: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', minWidth: 0 },
  drillObjective: { fontSize: '11.5px', fontWeight: 650, minWidth: 0, lineHeight: 1.45 },
  drillMeta: { color: COLORS.steelDim, fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums', fontFamily: MONO },
  drillLabel: { color: COLORS.steelDim, fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.09em', fontWeight: 650 },
  drillReason: { color: COLORS.steel, fontSize: '11.5px', lineHeight: 1.5 },
  taskRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', minWidth: 0 },
  taskMeta: { display: 'inline-flex', alignItems: 'center', gap: '8px', flexShrink: 0 },
  taskAttempts: { color: COLORS.steelDim, fontSize: '11px', fontVariantNumeric: 'tabular-nums', flexShrink: 0, fontFamily: MONO },
  taskGateChip: { display: 'inline-flex', alignItems: 'center', flexShrink: 0, fontSize: '10.5px', lineHeight: 1, border: `1px solid ${COLORS.frame}`, borderRadius: '2px', padding: '2px 6px', minHeight: '18px', fontVariantNumeric: 'tabular-nums', fontFamily: MONO, color: COLORS.steel, background: COLORS.flap },
  taskLessonChip: { display: 'inline-flex', alignItems: 'center', gap: '4px', flexShrink: 0, fontSize: '10.5px', lineHeight: 1, color: COLORS.amber, border: `1px solid rgba(255,176,0,0.4)`, borderRadius: '2px', padding: '2px 6px', minHeight: '18px', fontFamily: MONO, background: COLORS.flap },
  eventRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px', minWidth: 0 },
  eventType: { fontSize: '11.5px', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: MONO },
  childRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', minWidth: 0 },
  childStack: { display: 'grid', gap: '4px', minWidth: 0 },
  childStatusWrap: { position: 'relative', display: 'inline-flex', flexShrink: 0 },
  childStatusBtn: { display: 'inline-flex', alignItems: 'center', gap: '3px', minHeight: '22px', padding: '0 7px', border: `1px solid ${COLORS.frame}`, borderRadius: '2px', background: COLORS.flap, color: COLORS.steel, fontSize: '10.5px', cursor: 'pointer', fontFamily: MONO },
  childStatusMenu: { position: 'absolute', top: 'calc(100% + 4px)', right: 0, zIndex: 30, display: 'grid', minWidth: '132px', padding: '4px', border: `1px solid ${COLORS.frame}`, borderRadius: '5px', background: '#1a1d23', boxShadow: '0 10px 26px rgba(0,0,0,0.5)' },
  childStatusOption: { border: 0, background: 'transparent', color: COLORS.letter, fontSize: '11.5px', textAlign: 'left', padding: '6px 8px', borderRadius: '3px', cursor: 'pointer', fontFamily: COND },
  childStatusOptionCurrent: { color: COLORS.steelDim, cursor: 'default' },
  childStatusOptionDanger: { color: COLORS.red },
  memoryFilters: { display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' },
  memoryMatched: { color: COLORS.steelDim, fontSize: '11px', fontVariantNumeric: 'tabular-nums', marginTop: '6px', fontFamily: MONO },
  widgetChips: { display: 'flex', flexWrap: 'wrap', gap: '7px' },
  widgetChip: { display: 'inline-flex', alignItems: 'center', gap: '6px', minHeight: '28px', padding: '0 11px', border: `1px solid ${COLORS.frame}`, borderRadius: '3px', background: COLORS.flap, color: COLORS.letter, fontSize: '11px', cursor: 'pointer', fontFamily: MONO },
  widgetChipDisabled: { color: COLORS.steelDim, cursor: 'default', opacity: 0.7 },
  widgetChipCopied: { borderColor: COLORS.green, color: COLORS.green },
  stripGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '8px' },
  segRow: { display: 'inline-flex', gap: '3px' },
  segBtn: { minHeight: '23px', padding: '0 9px', border: `1px solid ${COLORS.frame}`, borderRadius: '2px', background: COLORS.flap, color: COLORS.steelDim, fontSize: '10.5px', cursor: 'pointer', fontVariantNumeric: 'tabular-nums', fontFamily: MONO },
  segBtnActive: { background: COLORS.amberDim, borderColor: COLORS.amber, color: COLORS.amber },
  // --- Board primitives ------------------------------------------------------
  boardSectionLabel: { display: 'flex', alignItems: 'center', gap: '8px', margin: '13px 0 6px', color: COLORS.steelDim, fontSize: '10px', fontWeight: 800, letterSpacing: '0.16em', textTransform: 'uppercase' },
  boardSectionLabelRule: { flex: 1, height: '1px', background: COLORS.seam },
  lampRow: { display: 'flex', gap: '5px', flexWrap: 'wrap' },
  lampCell: { display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '3px 8px', background: COLORS.flap, border: `1px solid ${COLORS.seam}`, borderRadius: '3px', fontSize: '9.5px', fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: COLORS.steelDim, fontFamily: COND },
  lampCellLit: { color: COLORS.letter, borderColor: 'rgba(255,176,0,0.35)' },
  lampDot: { width: '6px', height: '6px', borderRadius: '50%', background: '#2b2f37', flexShrink: 0 },
  lampDotLit: { boxShadow: '0 0 6px currentColor' },
  flipTile: { position: 'relative', display: 'inline-grid', placeItems: 'center', background: COLORS.flap, border: `1px solid ${COLORS.seam}`, borderRadius: '3px', padding: '1px 7px', overflow: 'hidden' },
  flipTileInner: { position: 'relative', zIndex: 1, fontVariantNumeric: 'tabular-nums' },
  flipTileSeam: { position: 'absolute', left: 0, right: 0, top: '50%', height: '1px', background: 'rgba(0,0,0,0.55)', zIndex: 2 },
  flipTileAnim: 'sips-flip-in'
}
// Adaptive polling: hidden windows and background panes don't need live data,
// so queries stretch their interval 4x while document.hidden. Callers pass
// their normal cadence; nothing changes while the panel is visible.
function pollInterval(baseMs) {
  try {
    return typeof document !== 'undefined' && document.hidden ? baseMs * 4 : baseMs
  } catch { return baseMs }
}

function toneFor(value) {
  const normalized = String(value || '').toLowerCase()
  if (['inspected', 'active', 'done', 'verified', 'connected', 'ready', 'healthy', 'ok', 'source_present'].includes(normalized)) return 'good'
  if (['not_inspected', 'paused', 'pending', 'unknown', 'loading', 'legacy', 'advisory_unavailable'].includes(normalized)) return 'warn'
  if (normalized.includes('unproven') || ['partial', 'degraded', 'incomplete'].includes(normalized)) return 'warn'
  if (normalized === 'stale') return 'muted'
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

const SIPS_TONE_HEX = { good: '#39d98a', warn: '#ffb000', bad: '#ff5a5a', muted: '#79808b', accent: '#ffb000', steelDim: '#79808b' }

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

// ---------------------------------------------------------------------------
// THE BOARD primitives — split-flap departures for live SIPS state.
// FlapCell: renders a value inside a flap tile with the seam line. FlipValue:
// re-mounts the tile (key = value) so a changed value flips in with the
// cascade animation; unchanged values never re-mount, so the board is calm
// between polls. All motion respects prefers-reduced-motion via CSS.
// ---------------------------------------------------------------------------

function FlapCell({ value, color, mono = true, title, style, weight = 650, size }) {
  return jsxs('span', {
    title,
    style: { ...styles.flipTile, ...(size ? { fontSize: size } : {}), ...(style || {}) },
    children: [
      jsx('span', { 'aria-hidden': true, style: styles.flipTileSeam }),
      jsx('span', {
        className: styles.flipTileAnim,
        style: { ...styles.flipTileInner, color: color || COLORS.letter, fontWeight: weight, ...(mono ? { fontFamily: MONO } : {}) },
        children: value
      })
    ]
  })
}

// Flip-on-change wrapper: keyed by the rendered value so React swaps the node
// (and the CSS flip animation runs) only when the value actually changes.
function FlipValue({ value, color, mono = true, title, weight, size, style }) {
  return jsx(FlapCell, { value, color, mono, title, weight, size, style, key: String(value) })
}


// Per-character flap digits: splits a value into fixed-cell tiles, each with
// the midline seam — the split-flap signature. Mono + tabular keeps digits
// uniform; per-char keys re-mount only changed characters.
function FlapDigits({ value, color, size = '18px', weight = 800 }) {
  const chars = String(value).split('')
  return jsx('span', {
    style: { display: 'inline-flex', gap: '2px', alignItems: 'center' },
    children: chars.map((ch, i) => ch === ' '
      ? jsx('span', { key: `sp-${i}`, style: { width: '4px' } })
      : jsx('span', {
          key: `${i}-${ch}`,
          className: styles.flipTileAnim,
          style: {
            display: 'inline-grid', placeItems: 'center',
            minWidth: '13px', padding: '2px 3px',
            background: COLORS.flap,
            border: `1px solid ${COLORS.seam}`,
            borderTopColor: 'rgba(255,255,255,0.13)',
            borderBottomColor: 'rgba(0,0,0,0.7)',
            borderRadius: '2px',
            position: 'relative',
            overflow: 'hidden',
            fontFamily: MONO,
            fontSize: size,
            fontWeight: weight,
            fontVariantNumeric: 'tabular-nums',
            color: color || COLORS.letter,
            lineHeight: 1
          },
          children: [
            jsx('span', { 'aria-hidden': true, style: { position: 'absolute', left: 0, right: 0, top: '50%', height: '1px', background: 'rgba(0,0,0,0.78)' } }),
            jsx('span', { 'aria-hidden': true, style: { position: 'absolute', left: 0, right: 0, top: 0, height: '50%', background: 'rgba(255,255,255,0.05)' } }),
            ch
          ]
        }))
  })
}

// Lamp row: status read as platform lamps — lit dot + label, unlit stays dark.
function LampRow({ items }) {
  return jsx('div', { style: styles.lampRow, children: items.map((item) => jsxs('span', {
    style: { ...styles.lampCell, ...(item.lit ? styles.lampCellLit : {}) },
    children: [
      jsx('span', {
        'aria-hidden': true,
        style: { ...styles.lampDot, ...(item.lit ? { ...styles.lampDotLit, background: item.color || COLORS.amber, color: item.color || COLORS.amber } : {}) }
      }),
      item.label
    ]
  }, item.label)) })
}

function Sparkline({ values, color = COLORS.amber }) {
  if (!values || values.length < 2) return null // no trend yet: leave the slot empty, the detail line already explains

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
      jsx('line', { x1: '0', y1: '22', x2: '100', y2: '22', stroke: 'rgba(139,145,155,0.25)', strokeWidth: '1' }),
      jsx('polyline', { points, fill: 'none', stroke: color, strokeWidth: '2', strokeLinecap: 'round', strokeLinejoin: 'round' })
    ]
  })
}

function toneColor(value) {
  return COLORS[toneFor(value)] || COLORS.muted
}

// Unicode block sparkline (▁▂▃▄▅▆▇█) over the 24h lifecycle histogram
// ({hour, events} points, oldest -> newest). Returns { chars, title } or null
// when there are fewer than two points. Series shorter than 8 chars are
// left-padded with baseline blocks so the shape stays readable.
function histogramSparkline(histogram) {
  const points = (Array.isArray(histogram) ? histogram : [])
    .map((col) => ({ hour: String(col?.hour || ''), events: Number(col?.events) || 0 }))
  if (points.length < 2) return null
  const blocks = '▁▂▃▄▅▆▇█'
  const max = Math.max(...points.map((point) => point.events), 1)
  let chars = points.map((point) => blocks[Math.min(blocks.length - 1, Math.round((point.events / max) * (blocks.length - 1)))]).join('')
  if (chars.length < 8) chars = blocks[0].repeat(8 - chars.length) + chars
  const peak = points.reduce((best, point) => (point.events > best.events ? point : best), points[0])
  return { chars, title: `24h activity · peak ${peak.hour} (${peak.events} event${peak.events === 1 ? '' : 's'})` }
}

function StateBadge({ value, tone }) {
  const color = tone ? (TONE_LAMP[tone] || COLORS.steel) : toneColor(value)

  return jsx(Badge, {
    variant: 'outline',
    style: {
      color,
      borderColor: `${color}55`,
      background: 'rgba(0,0,0,0.35)',
      fontSize: '10px',
      fontFamily: MONO,
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      fontWeight: 700,
      borderRadius: '3px',
      padding: '1px 7px'
    },
    children: formatStatus(value)
  })
}

function Card({ title, icon, hint, lead = false, actions, children }) {
  return jsx('section', {
    style: { ...styles.card, ...(lead ? styles.moduleLead : styles.module) },
    'data-sips-card': true,
    'data-sips-lead': lead ? true : undefined,
    children: [
      jsx('div', { style: styles.screwPlate, 'aria-hidden': true, children: [jsx('span', { style: styles.screw }), jsx('span', { style: styles.screw })] }),
      jsx('div', { style: styles.cardTitle, children: [
        jsx(Codicon, { name: icon, size: '0.95rem', style: { color: COLORS.amber } }),
        jsx('span', { children: title }),
        actions ? jsx('span', { style: { marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: '8px' }, children: actions }) : null
      ] }),
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
  for (let i = 0; i <= 16; i++) {
    const tickAngle = -120 + (i / 16) * 240
    const major = i % 2 === 0
    ticks.push(jsx('div', {
      key: i,
      style: {
        position: 'absolute', left: '50%', top: '50%', width: '1.5px',
        height: major ? '8px' : '4px',
        marginLeft: '-0.75px',
        background: major ? COLORS.steelDim : 'rgba(139,145,155,0.3)',
        transformOrigin: 'center top',
        transform: `translateY(-${size * 0.42}px) rotate(${tickAngle}deg) translateY(${size * 0.42}px)`
      }
    }))
  }
  return jsx('div', { style: { ...styles.gaugeWrap, width: `${size}px`, height: `${size}px` }, role: 'img', 'aria-label': `${label}: ${clamped}%`, children: [
    jsx('div', { style: styles.dialFace }),
    jsx('div', { style: { ...styles.dialTicks }, children: ticks }),
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
        style: { position: 'absolute', inset: 0, borderRadius: '999px', background: on ? 'rgba(57,217,138,0.22)' : 'transparent', border: on ? `1px solid rgba(57,217,138,0.5)` : '1px solid transparent', transition: 'background 160ms ease, border-color 160ms ease' }
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


function Signal({ label, value, detail, tone = 'accent', progress, trend, trendUnit = 'pts', spark }) {
  const color = tone === 'accent' ? COLORS.letter : TONE_LAMP[tone] || COLORS.letter

  const lamp = TONE_LAMP[tone] || COLORS.amber
  return jsx('div', {
    style: styles.signal,
    children: [
      jsx('div', { style: { ...styles.signalLabel, display: 'flex', alignItems: 'center', gap: '6px' }, children: [
        jsx('span', { 'aria-hidden': true, style: { width: '5px', height: '5px', borderRadius: '50%', background: lamp, boxShadow: `0 0 5px ${lamp}88`, flexShrink: 0 } }),
        label
      ] }),
      jsxs('div', { style: { ...styles.signalValue, color, display: 'flex', alignItems: 'baseline', gap: '8px', minWidth: 0 }, children: [
        String(value).length <= 10 ? jsx(FlapDigits, { value, color }) : jsx(FlapCell, { value, color, title: value, style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '100%' } }),
        spark ? jsx('span', {
          title: spark.title,
          'aria-label': spark.title,
          style: { fontFamily: 'var(--ui-mono, ui-monospace, monospace)', fontSize: '12px', fontWeight: 400, color: COLORS.muted, letterSpacing: '1px', lineHeight: 1, flexShrink: 0 },
          children: spark.chars
        }) : null
      ] }),
      jsx('div', { style: styles.signalDetail, title: detail, children: detail }),
      progress === undefined ? null : jsx('div', {
        style: styles.signalTrack,
        children: jsx('div', { style: { ...styles.miniFill, background: color, transform: `scaleX(${Math.max(0, Math.min(1, (Number(progress) || 0) / 100))})` } })
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
  const postureColor = TONE_LAMP[posture.tone] || COLORS.steelDim
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
  const freshnessColor = fetchError || (ageSeconds !== undefined && ageSeconds >= 60) ? COLORS.amber : COLORS.green
  const surfaceTrend = history.map((sample) => sample.surfaceTotal)
  const memoryTrend = history.map((sample) => sample.memoryVerified)
  const lifecycleTrend = history.map((sample) => sample.lifecycle)
  const lifecycleSpark = histogramSparkline(data?.lifecycle?.histogram)

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
      jsx('div', { style: { ...styles.heroGlow, display: 'none' }, 'aria-hidden': true }),
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
              jsx('div', { style: styles.eyebrow, children: 'LIVE POSTURE' }),
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
                jsx(Dial, { value: posture.coverage, color: SIPS_TONE_HEX[posture.tone] || SIPS_TONE_HEX.steelDim, label: 'proof coverage' }),
                jsx('div', { style: { textAlign: 'left' }, children: [
                  jsx(FlapDigits, { value: `${posture.readyProof}/${posture.totalProof || 0}`, color: postureColor, size: '16px' }),
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
          jsx(Signal, { label: 'Proof coverage', value: `${posture.readyProof}/${posture.totalProof || 0}`, detail: `${posture.coverage}% of layers ready`, tone: posture.tone, progress: posture.coverage, trend: proofTrend }),
          jsx(Signal, { label: 'Surface area', value: compactNumber(surfaceTotal), detail: 'declared capabilities', trend: surfaceTrend, trendUnit: '' }),
          jsx(Signal, { label: 'Memory verified', value: compactNumber(memory.verified_or_active_count || 0), detail: memory.available ? `${compactNumber(memory.record_count || 0)} total records` : 'memory unavailable', tone: memory.available ? 'good' : 'warn', trend: memoryTrend, trendUnit: '' }),
          jsx(Signal, { label: 'Lifecycle', value: compactNumber(data?.events?.event_count || 0), detail: 'recorded events', trend: lifecycleTrend, trendUnit: '', spark: lifecycleSpark })
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
  const goalQuery = useQuery({ queryKey: ['sips-control-plane', 'goal'], queryFn: () => api.rest('/goal'), refetchInterval: pollInterval(30000) })
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

// Unified Goal Board: runtime projection joined with legacy goal state.
// One board: authority, phase strip, ready tasks, and the recommendation.
function GoalBoardCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'goal-board'], queryFn: () => api.rest('/goal-board'), refetchInterval: pollInterval(20000) })

  if (query.isLoading) {
    return jsx(Card, { title: 'Goal board', icon: 'target', lead: true, children: jsx('div', { style: styles.unavailable, children: 'Reading the board…' }) })
  }
  if (query.isError) {
    return jsx(Card, { title: 'Goal board', icon: 'target', lead: true, children: jsx('div', { style: styles.unavailable, children: 'The goal-board endpoint is unavailable right now.' }) })
  }
  const board = query.data
  const goal = board?.goal || {}
  const runtime = board?.runtime
  const phases = board?.phases || []
  const tasks = board?.runtime_tasks || []
  const recommendation = board?.recommendation
  const progress = runtime?.progress || { complete: 0, total: 0 }
  const total = progress.total || goal.subtasks?.total || 0
  const complete = progress.complete || goal.subtasks?.done || 0
  const boardStatus = runtime?.status || goal.status || 'none'
  const glyph = boardStatus === 'running' || boardStatus === 'active' ? '◐' : boardStatus === 'succeeded' || boardStatus === 'done' ? '✓' : boardStatus === 'failed' ? '✗' : '○'

  return jsx(Card, {
    title: 'Goal board',
    icon: 'target',
    lead: true,
    hint: `authority: ${board?.authority || 'none'}${runtime?.run_id ? ` · run ${runtime.run_id}` : ''}${runtime ? ` · rev ${runtime.revision}` : ''}`,
    children: [
      jsxs('div', { style: { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }, children: [
        jsx('span', { 'aria-hidden': true, style: { fontSize: '15px', color: boardStatus === 'failed' ? COLORS.bad : boardStatus === 'running' || boardStatus === 'active' ? COLORS.accent : COLORS.muted }, children: glyph }),
        jsx('span', { style: { ...styles.objective, flex: 1, minWidth: 0 }, children: goal.objective || runtime?.run_id || 'No active goal — the board fills when /goal or /selfloop starts one.' })
      ] }, 'head'),
      total ? jsxs('div', { key: 'progress', children: [
        jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }, children: [
          jsx('span', { style: styles.label, children: 'Progress' }),
          jsx(FlapDigits, { value: `${complete}/${total}`, size: '12px', weight: 750 })
        ] }),
        jsx('div', { style: styles.progressTrack, children: complete > 0 ? jsx('div', { className: 'sips-progress-fill', style: { ...styles.progressFill, width: `${Math.round((complete / total) * 100)}%` } }) : null })
      ] }) : null,
      phases.length ? jsx('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '6px', margin: '11px 0 2px' }, key: 'phases', children: phases.map((phase) => jsxs('span', {
        style: {
          display: 'inline-flex', alignItems: 'center', gap: '5px',
          padding: '3px 9px', borderRadius: '999px', fontSize: '11px', fontWeight: 650,
          border: `1px solid ${phase.status === 'active' ? 'rgba(255,176,0,0.45)' : COLORS.seam}`,
          color: phase.status === 'active' ? COLORS.amber : COLORS.steelDim,
          fontFamily: MONO, textTransform: 'uppercase', letterSpacing: '0.06em', background: COLORS.flap
        },
        children: [
          jsx('span', { 'aria-hidden': true, style: { width: '6px', height: '6px', borderRadius: '50%', background: phase.status === 'active' ? COLORS.amber : phase.status === 'done' ? COLORS.green : '#2b2f37', boxShadow: phase.status === 'active' ? `0 0 6px ${COLORS.amber}88` : 'none', flexShrink: 0 } }),
          ' ', phase.title
        ]
      }, phase.title)) }) : null,
      tasks.length ? jsx('div', { style: { marginTop: '8px' }, key: 'tasks', children: tasks.slice(0, 5).map((task) => jsxs('div', { style: styles.row, children: [
        jsxs('span', { style: { fontSize: '12px', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: [
          jsx('span', { 'aria-hidden': true, style: { marginRight: '6px', color: task.status === 'succeeded' ? COLORS.good : task.status === 'failed' ? COLORS.bad : task.ready ? COLORS.accent : COLORS.muted }, children: task.status === 'succeeded' ? '✓' : task.status === 'failed' ? '✗' : task.ready ? '◉' : '○' }),
          task.title || task.id
        ] }),
        jsxs('span', { style: { ...styles.value, flexShrink: 0 }, children: [
          task.ready && task.status !== 'succeeded' ? jsx('span', { style: { color: COLORS.accent, marginRight: '6px', fontSize: '10px', fontWeight: 700 }, children: 'READY' }) : null,
          jsx(StateBadge, { value: task.status })
        ] })
      ] }, task.id)) }) : null,
      recommendation ? jsx('div', {
        style: { marginTop: '11px', border: `1px solid ${COLORS.accent}`, borderRadius: '10px', padding: '10px 12px', background: 'rgba(125,211,252,0.06)' },
        key: 'rec',
        children: [
          jsxs('div', { style: { fontSize: '12px', fontWeight: 700 }, children: ['Next: ', recommendation.title || recommendation.phase] }),
          recommendation.why ? jsx('div', { style: { ...styles.label, marginTop: '4px', lineHeight: 1.5 }, children: recommendation.why }) : null,
          recommendation.proof_required ? jsx('div', { style: { ...styles.label, marginTop: '3px', lineHeight: 1.5, color: COLORS.warn }, children: `Proof: ${recommendation.proof_required}` }) : null
        ]
      }) : null,
      jsx('div', { style: { ...styles.label, fontSize: '11px', marginTop: '11px', lineHeight: 1.5 }, key: 'boundary', children: board?.claim_boundary })
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
    hint: `${goal.mode || 'legacy'} mode · ${goal.turn_count || 0} turn${goal.turn_count === 1 ? '' : 's'} · ${goal.cycle_count || 0} cycle${goal.cycle_count === 1 ? '' : 's'}`,
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
      total ? jsxs('div', { children: [
        jsx('div', {
          style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' },
          children: [jsx('span', { style: styles.label, children: 'Subtask progress' }), jsx(FlipValue, { value: `${done}/${total}`, weight: 750 })]
        }),
        jsx('div', { style: styles.progressTrack, children: jsx('div', { className: 'sips-progress-fill', style: { ...styles.progressFill, width: `${progress}%`, background: goalColor } }) })
      ] }) : null,
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
  const query = useQuery({ queryKey: ['sips-control-plane', 'action-history'], queryFn: () => api.rest('/action-history'), refetchInterval: pollInterval(20000) })

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

// Gate matrix: per-run verification receipts from /gate-matrix. One dense row
// per recent run (newest first), one cell per gate colored by outcome. Runs
// without a receipt (active/legacy) carry all-null gates and read as
// 'not yet gated' rather than as a pass or a failure.
function GateMatrixCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'gate-matrix'], queryFn: () => api.rest('/gate-matrix'), refetchInterval: pollInterval(30000) })
  const title = 'Gate matrix'
  const icon = 'verified'

  if (query.isLoading) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'Reading gate receipts…' }) })
  }
  if (query.isError || !query.data?.available) {
    return jsx(Card, {
      title,
      icon,
      hint: 'Per-run gate outcomes from verification receipts.',
      children: jsx('div', { style: styles.unavailable, children: query.data?.reason || 'The gate matrix is unavailable right now.' })
    })
  }

  const data = query.data
  const gates = data.gates || []
  const runs = (data.runs || []).slice(0, 12)
  const gatedRuns = runs.filter((run) => run.receipt)
  const cleanRuns = gatedRuns.filter((run) => !run.failed_count).length
  const gateColor = (state) => state === 'ok' ? COLORS.good : state === 'failed' ? COLORS.bad : state === 'partial' ? COLORS.warn : COLORS.muted
  const gateText = (state) => state === 'ok' ? 'ok' : state === 'failed' ? 'FAIL' : state === 'partial' ? 'part' : state === 'skipped' ? 'skip' : state === 'unknown' ? '?' : '—'

  const columns = `minmax(0, 1fr) repeat(${Math.max(gates.length, 1)}, 38px) minmax(76px, auto)`
  const headStyle = { ...styles.label, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', textAlign: 'center', borderBottom: `1px solid ${COLORS.border}`, paddingBottom: '4px' }
  const cells = [
    jsx('div', { key: 'gm-h-run', style: { ...headStyle, textAlign: 'left' }, children: 'run' }),
    ...gates.map((gate) => jsx('div', { key: `gm-h-${gate}`, style: headStyle, children: gate.slice(0, 4) })),
    jsx('div', { key: 'gm-h-count', style: headStyle, children: 'ok·fail' })
  ]
  for (const run of runs) {
    const gated = Boolean(run.receipt)
    cells.push(jsx('div', {
      key: `gm-run-${run.run_id}`,
      title: `${run.run_id} · ${formatRelativeTimestamp(run.updated_at)}${gated ? '' : ' · not yet gated'}`,
      style: { fontSize: '11px', fontFamily: 'var(--ui-mono, ui-monospace, monospace)', color: gated ? COLORS.text : COLORS.muted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
      children: run.run_id
    }, `gm-run-${run.run_id}`))
    for (const gate of gates) {
      const state = gated ? run.gates?.[gate] : null
      cells.push(jsx('div', {
        key: `gm-${run.run_id}-${gate}`,
        title: `${run.run_id} · ${gate}: ${state || 'not yet gated'}`,
        style: { fontSize: '10px', fontFamily: 'var(--ui-mono, ui-monospace, monospace)', color: gateColor(state), textAlign: 'center', fontVariantNumeric: 'tabular-nums' },
        children: gated ? gateText(state) : '—'
      }, `gm-${run.run_id}-${gate}`))
    }
    cells.push(jsx('div', {
      key: `gm-count-${run.run_id}`,
      title: gated ? `${run.run_id} · ${run.ok_count || 0} ok, ${run.failed_count || 0} failed` : `${run.run_id} · not yet gated`,
      style: gated
        ? { fontSize: '11px', fontVariantNumeric: 'tabular-nums', color: run.failed_count ? COLORS.bad : COLORS.muted, textAlign: 'right', whiteSpace: 'nowrap' }
        : { ...styles.label, fontSize: '10px', textAlign: 'right', whiteSpace: 'nowrap' },
      children: gated ? `${run.ok_count || 0}·${run.failed_count || 0}` : 'not yet gated'
    }, `gm-count-${run.run_id}`))
  }

  return jsx(Card, {
    title,
    icon,
    hint: `${gatedRuns.length}/${runs.length} runs gated · ${cleanRuns} clean · ${data.claim_boundary || ''}`,
    children: runs.length ? jsx('div', {
      style: { display: 'grid', gridTemplateColumns: columns, gap: '3px 6px', alignItems: 'center', minWidth: 0 },
      children: cells
    }) : jsx('div', { style: styles.unavailable, children: 'No runs recorded yet — the matrix fills as runs complete.' })
  })
}

function RoutesCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'routes'], queryFn: () => api.rest('/routes'), refetchInterval: pollInterval(60000) })
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
  const query = useQuery({ queryKey: ['sips-control-plane', 'runtime'], queryFn: () => api.rest('/runtime'), refetchInterval: pollInterval(20000) })

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
  const budget = runtime.budget || null
  const charged = Number(budget?.charged_tokens) || 0
  const released = Number(budget?.released_token_limit) || 0
  const trancheLimits = budget?.tranche_limits || []
  const currentTranche = trancheLimits.length ? trancheLimits[Math.min(Number(budget?.released_tranches) || 1, trancheLimits.length) - 1] : released
  const spendRatio = currentTranche ? Math.min(100, Math.round(charged / currentTranche * 100)) : 0
  const spendTone = budget?.soft_exceeded ? 'warn' : spendRatio >= 90 ? 'warn' : spendRatio >= 100 ? 'bad' : 'good'
  const overTranche = currentTranche && charged > currentTranche
  const resourceRows = budget ? Object.entries(budget.resource_limits || {})
    .filter(([key]) => !['model_tokens', 'output_tokens', 'retrieval_tokens'].includes(key))
    .map(([key, limit]) => ({ key, limit, used: (budget.resources || {})[key] || 0 }))
    .filter((row) => row.limit > 0 && row.used > 0) : []

  const fmtCompact = (n) => {
    const v = Number(n) || 0
    if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`
    if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`
    if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`
    return String(v)
  }

  return jsx(Card, {
    title: 'Runtime goal board',
    icon: 'target',
    hint: `Run ${runtime.run_id || '?'} · rev ${runtime.revision ?? '?'} · authority ${runtime.authority || 'unknown'}`,
    children: [
      jsx('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }, children: [
        jsx('span', { style: styles.label, children: runtime.objective || 'Session work' }),
        jsx(StateBadge, { value: runtime.status, tone: boardTone })
      ] }),
      jsx('div', { style: styles.memoryTrack, role: 'img', 'aria-label': `Run progress ${progress.complete}/${progress.total}`, children: [
        jsx('div', { className: 'sips-progress-fill', style: { width: `${ratio}%`, background: COLORS.amber } }),
        jsx('div', { style: { ...styles.memoryOther, width: `${100 - ratio}%` } })
      ] }),
      jsx('div', { style: styles.row, children: [
        jsx('span', { style: styles.label, children: 'Task progress' }),
        jsx('span', { style: { ...styles.value, fontVariantNumeric: 'tabular-nums' }, children: `${progress.complete}/${progress.total}` })
      ] }),
      budget ? jsxs('div', { style: { marginTop: '10px', display: 'grid', gap: '5px' }, children: [
        jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }, children: [
          jsx('span', { style: { ...styles.label, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em' }, children: `Budget · tranche ${budget.released_tranches ?? '—'}/${trancheLimits.length || '—'} released` }),
          jsxs('span', { style: { fontSize: '11px', fontVariantNumeric: 'tabular-nums' }, children: [
            jsx(FlipValue, { value: fmtCompact(charged), color: budget.soft_exceeded ? COLORS.amber : COLORS.letter, weight: 750 }),
            jsx('span', { style: { color: COLORS.steelDim, fontFamily: MONO }, children: ` / ${fmtCompact(currentTranche)}` })
          ] })
        ] }),
        jsx('div', {
          style: { height: '6px', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' },
          role: 'img',
          'aria-label': `Budget: ${fmtCompact(charged)} of ${fmtCompact(currentTranche)} tranche tokens charged (${spendRatio}%)`,
          children: jsx('div', { style: { height: '100%', width: `${spendRatio}%`, borderRadius: '999px', background: COLORS[spendTone], opacity: 0.8 } })
        }),
        overTranche && trancheLimits.length > (Number(budget.released_tranches) || 1) ? jsx('div', { style: { ...styles.label, fontSize: '10px', color: COLORS.warn }, children: `Soft budget exceeded — next tranche releases at ${fmtCompact(trancheLimits[Math.min(Number(budget.released_tranches) || 1, trancheLimits.length)])}` }) : null,
        budget.soft_exceeded ? jsx('div', { style: { ...styles.label, fontSize: '10px', color: COLORS.warn }, children: 'Reservation exceeds soft limit — charged at lease time, nothing is gated; tranches release on demand' }) : null,
        resourceRows.length ? jsx('div', { style: { display: 'grid', gap: '6px', marginTop: '6px' }, children: resourceRows.map((row) => {
          const ratio = Math.min(1, row.used / row.limit)
          const hot = ratio >= 0.9
          return jsxs('div', { style: { display: 'grid', gap: '3px' }, children: [
            jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }, children: [
              jsx('span', { style: { fontSize: '10.5px', fontFamily: MONO, textTransform: 'uppercase', letterSpacing: '0.07em', color: COLORS.steelDim, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: formatStatus(row.key) }),
              jsx('span', { style: { flexShrink: 0, fontSize: '11px', fontVariantNumeric: 'tabular-nums', fontFamily: MONO, color: hot ? COLORS.amber : COLORS.steel }, children: `${fmtCompact(row.used)} / ${fmtCompact(row.limit)}` })
            ] }),
            jsx('div', { style: styles.miniTrack, role: 'img', 'aria-label': `${row.key}: ${fmtCompact(row.used)} of ${fmtCompact(row.limit)}`, children: jsx('div', { style: { height: '100%', width: `${ratio * 100}%`, background: hot ? COLORS.amber : COLORS.steelDim } }) })
          ] }, `res-${row.key}`)
        }) }) : null
      ] }) : null,
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

function runStatusTone(status) {
  if (status === 'running') return 'accent'
  if (status === 'succeeded') return 'good'
  if (status === 'stale') return 'muted' // stale is the resting state, not an alarm
  if (status === 'failed') return 'bad'
  return 'muted'
}

// --- Drill-down helpers ------------------------------------------------------
// Shared expand/collapse + lazy-detail-fetch used by RunsCard and FleetCard.
// Only ONE row is expanded per card: clicking another row collapses the first;
// clicking the expanded row again collapses it. Detail fetches are gated by
// useQuery `enabled`, so collapsed rows cost nothing.

function DrillDownRow({ id, expanded, onToggle, children, detail }) {
  return jsx('div', { children: [
    jsxs('div', {
      role: 'button',
      tabIndex: 0,
      'aria-expanded': expanded,
      onClick: () => onToggle(id),
      onKeyDown: (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onToggle(id) } },
      style: styles.drillRow,
      children: [
        jsx('span', {
          'aria-hidden': true,
          style: { ...styles.drillChevron, transform: expanded ? 'rotate(90deg)' : 'none' },
          children: jsx(Codicon, { name: 'chevron-right', size: '0.8rem' })
        }),
        jsx('div', { style: styles.drillBody, children })
      ]
    }),
    expanded ? jsx('div', { style: styles.drillPanel, children: detail }) : null
  ] }, `drill-${id}`)
}

function truncateMiddle(text, max = 48) {
  const value = String(text || '')
  if (value.length <= max) return value
  const head = Math.ceil((max - 1) / 2)
  const tail = Math.floor((max - 1) / 2)
  return `${value.slice(0, head)}…${value.slice(value.length - tail)}`
}

function compactBudgets(budgets, usage) {
  const budgetEntries = Object.entries(budgets || {})
  if (!budgetEntries.length) return null
  return budgetEntries
    .map(([key, hard]) => {
      const charged = (usage || {})[key]
      return `${key} ${charged === undefined ? '—' : compactNumber(charged)} / ${compactNumber(hard)}`
    })
    .join(' · ')
}

// --- Run quality -------------------------------------------------------------
// /runs/{id}/quality (sips.run-quality.v1) is unavailable for runs without a
// receipt (running/legacy), so both surfaces degrade to a muted reason line.
// The query key is shared between RunDetail's compact line and RunQualityCard,
// so one fetch serves both surfaces while a run's detail is expanded.
function useRunQualityQuery(api, runId) {
  return useQuery({
    queryKey: ['sips-control-plane', 'run-quality', runId],
    queryFn: () => api.rest(`/runs/${encodeURIComponent(runId)}/quality`),
    enabled: Boolean(runId),
    staleTime: 15000,
    refetchInterval: pollInterval(30000)
  })
}

function runQualityTone(status) {
  if (status === 'ok') return 'good'
  if (status === 'failed') return 'bad'
  if (status === 'partial') return 'warn'
  return 'muted'
}

// 'gates 5/5 ok · impact normal · evidence 3170 items' — null while the fetch
// has not landed or the run has no quality receipt yet.
function compactQualityLine(quality) {
  if (!quality?.available) return null
  const gates = quality.gates || []
  const okCount = gates.filter((gate) => gate.status === 'ok').length
  const evidenceTotal = gates.reduce((sum, gate) => sum + (Number(gate.evidence_total) || 0), 0)
  const segments = []
  if (gates.length) segments.push(`gates ${okCount}/${gates.length} ok`)
  if (quality.impact) segments.push(`impact ${quality.impact}`)
  if (evidenceTotal > 0) segments.push(`evidence ${compactNumber(evidenceTotal)} items`)
  return segments.join(' · ')
}

// Expanded-quality surface inside the run drill-down: per-gate rows with a
// colored status chip + evidence total (first reason on failed/partial gates),
// impact/risk/reviewer tag chips, and the token-budget bar (warn at >=90%,
// TokenUsageCard bar idioms). Fetches via the shared run-quality query key.
function RunQualityCard({ api, runId }) {
  const query = useRunQualityQuery(api, runId)
  if (query.isLoading) {
    return jsx('div', { style: styles.drillReason, children: 'Reading run quality…' })
  }
  const quality = query.data
  if (query.isError || !quality?.available) {
    return jsx('div', { style: styles.drillReason, children: query.isError
      ? `Run quality failed to load: ${query.error?.message || 'unknown error'}`
      : quality?.reason || 'Run quality is unavailable for this run.' })
  }
  const gates = quality.gates || []
  const budget = quality.budget_usage
  const charged = Number(budget?.charged_tokens) || 0
  const limit = Number(budget?.released_token_limit) || 0
  const budgetShare = limit > 0 ? charged / limit : 0
  const chips = [
    ...(quality.impact ? [{ text: quality.impact, title: 'Impact', color: COLORS.accent }] : []),
    ...(quality.risk_tags || []).map((tag) => ({ text: tag, title: 'Risk tag', color: COLORS.warn })),
    ...(quality.reviewer_tags || []).map((tag) => ({ text: tag, title: 'Reviewer tag', color: COLORS.muted }))
  ]
  return jsxs('div', { style: styles.drillStack, children: [
    gates.length ? jsxs('div', { style: styles.drillStack, children: [
      jsx('div', { style: styles.drillLabel, children: 'Gates' }),
      ...gates.map((gate, index) => jsxs('div', { style: styles.drillStack, children: [
        jsxs('div', { style: styles.eventRow, children: [
          jsx('span', { style: styles.label, title: (gate.reasons || []).join('; ') || undefined, children: formatStatus(gate.name) }),
          jsxs('span', { style: styles.taskMeta, children: [
            Number(gate.evidence_total) > 0 ? jsx('span', { style: styles.taskAttempts, children: `${compactNumber(Number(gate.evidence_total))} ev` }) : null,
            jsx('span', { style: { ...styles.taskGateChip, color: COLORS[runQualityTone(gate.status)] }, children: formatStatus(gate.status) })
          ] })
        ] }),
        (gate.status === 'failed' || gate.status === 'partial') && (gate.reasons || []).length ? jsx('div', { style: { ...styles.drillMeta, whiteSpace: 'normal', lineHeight: 1.45, color: gate.status === 'failed' ? COLORS.bad : COLORS.warn }, children: gate.reasons[0] }) : null
      ] }, `qg-${gate.name || index}`))
    ] }) : null,
    chips.length ? jsx('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }, children: chips.map((chip, index) => jsx('span', {
      title: `${chip.title}: ${chip.text}`,
      style: { ...styles.taskGateChip, color: chip.color },
      children: chip.text
    }, `qc-${index}`)) }) : null,
    budget ? jsxs('div', { style: styles.drillStack, children: [
      jsxs('div', { style: styles.eventRow, children: [
        jsx('span', { style: styles.drillLabel, children: 'Token budget' }),
        jsx('span', { style: { ...styles.taskAttempts, color: budgetShare >= 0.9 ? COLORS.warn : COLORS.muted }, children: `${compactNumber(charged)} / ${compactNumber(limit)} tok` })
      ] }),
      jsx('div', {
        role: 'img',
        'aria-label': `Token budget: ${charged} of ${limit} charged`,
        style: { height: '5px', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' },
        children: jsx('div', { style: { height: '100%', width: `${Math.min(100, budgetShare * 100)}%`, borderRadius: '999px', background: budgetShare >= 0.9 ? COLORS.warn : COLORS.accent, opacity: 0.7 } })
      })
    ] }) : null,
    quality.claim_boundary ? jsx('div', { style: styles.drillReason, children: quality.claim_boundary }) : null
  ] })
}

// --- Run annotator ----------------------------------------------------------
// Compact label affordance in the expanded run panel: the newest label shows
// as a badge next to the status; a one-line input (Enter or Add) POSTs the
// annotation. Input clears and shows brief inline feedback on success only —
// the text stays for correction when the write fails.
function RunAnnotator({ api, runId, label }) {
  const [draft, setDraft] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [feedbackError, setFeedbackError] = useState(false)
  const queryClient = useQueryClient()
  const mutation = useSipsMutation(api, {
    invalidateKeys: ['runs'],
    onSuccess: (result) => {
      if (result?.available) {
        setFeedback(`Labeled "${result.label}"`)
        setFeedbackError(false)
        setDraft('')
      } else {
        setFeedback(`Annotate failed: ${result?.reason || 'unknown reason'}`)
        setFeedbackError(true)
      }
      // useSipsMutation's string invalidateKeys cover the runs list; the
      // run-scoped detail key needs the full array, invalidated explicitly.
      queryClient.invalidateQueries({ queryKey: ['sips-control-plane', 'run-detail', runId] })
    },
    onError: (error) => {
      setFeedback(`Annotate failed: ${error.message || 'unknown error'}`)
      setFeedbackError(true)
    }
  })
  const busy = mutation.isPending || mutation.isLoading
  const submit = () => {
    const trimmed = draft.trim()
    if (!trimmed || busy) return
    setFeedback(null)
    setFeedbackError(false)
    mutation.mutate({ path: `/runs/${encodeURIComponent(runId)}/annotate`, body: { label: trimmed } })
  }

  return jsxs('div', { style: styles.drillStack, children: [
    jsxs('div', { style: styles.controlRow, children: [
      jsx('input', {
        style: styles.input,
        value: draft,
        placeholder: 'Label this run…',
        'aria-label': 'Annotate run label',
        onChange: (event) => setDraft(event.target.value),
        onKeyDown: (event) => { if (event.key === 'Enter') submit() }
      }),
      jsx(Button, {
        variant: 'outline',
        size: 'sm',
        disabled: busy || !draft.trim(),
        onClick: submit,
        children: busy ? 'Adding…' : 'Add'
      })
    ] }),
    feedback ? jsx(FleetComposerFeedback, { feedback, error: feedbackError }) : null
  ] })
}

function RunDetail({ api, runId }) {
  const query = useQuery({
    queryKey: ['sips-control-plane', 'run-detail', runId],
    queryFn: () => api.rest(`/runs/${encodeURIComponent(runId)}`),
    enabled: Boolean(runId),
    staleTime: 15000,
    refetchInterval: pollInterval(30000)
  })
  const qualityQuery = useRunQualityQuery(api, runId)
  const [copiedRunId, setCopiedRunId] = useState(false)
  const [qualityOpen, setQualityOpen] = useState(false)
  const copyRunId = () => {
    if (!runId || !navigator.clipboard?.writeText) return
    navigator.clipboard.writeText(runId).then(() => {
      setCopiedRunId(true)
      setTimeout(() => setCopiedRunId(false), 1500)
    }).catch(() => { /* clipboard unavailable — id stays selectable in tooltips */ })
  }

  if (query.isLoading) {
    return jsx('div', { style: { display: 'grid', placeItems: 'center', padding: '6px 0' }, children: jsx(Loader, { type: 'lemniscate-bloom' }) })
  }
  const detail = query.data
  if (!detail?.available) {
    return jsx('div', { style: styles.drillReason, children: detail?.reason || 'Run detail is unavailable.' })
  }
  const budgetsLine = compactBudgets(detail.budgets, detail.budget_usage)
  const qualityLine = compactQualityLine(qualityQuery.data)
  const tasks = detail.tasks || []
  const taskTokens = tasks.reduce((sum, task) => sum + (Number(task.tokens) || 0), 0)
  const events = (detail.events || []).slice() // chronological; most recent last
  const [allEvents, setAllEvents] = useState(false)
  const deepEvents = useQuery({
    queryKey: ['sips-control-plane', 'run-events', runId],
    queryFn: () => api.rest(`/runs/${encodeURIComponent(runId)}/events?limit=50`),
    enabled: allEvents,
    refetchInterval: pollInterval(30000)
  })
  const deepList = allEvents && deepEvents.data?.available ? (deepEvents.data.events || []) : []
  const showDeep = deepList.length > events.length
  // Shallow strip shows at most 6 rows until expanded; the deep fetch (when it
  // lands, or errors → fallback) replaces the cap with the full trail.
  const trailEvents = showDeep ? deepList : allEvents ? events : events.slice(0, 6)

  return jsxs('div', { style: styles.drillStack, children: [
    jsxs('div', { style: styles.drillHead, children: [
      jsx(StateBadge, { value: detail.status, tone: runStatusTone(detail.status) }),
      jsx('button', {
        type: 'button',
        onClick: copyRunId,
        title: runId,
        'aria-label': `Copy run id ${runId}`,
        style: { border: `1px solid ${COLORS.border}`, borderRadius: '6px', background: 'transparent', color: copiedRunId ? COLORS.good : COLORS.muted, fontSize: '11px', fontFamily: 'ui-monospace, monospace', padding: '1px 8px', cursor: navigator.clipboard ? 'pointer' : 'default', flexShrink: 0, fontVariantNumeric: 'tabular-nums' },
        children: copiedRunId ? 'Copied' : truncateMiddle(runId, 20)
      }),
      (detail.labels || []).length ? jsx(Badge, { variant: 'outline', title: (detail.labels || []).map((entry) => entry.label).join(' · '), style: { ...styles.metaBadge, color: COLORS.accent, borderColor: COLORS.accent }, children: detail.labels[detail.labels.length - 1].label }) : null,
      detail.objective ? jsx('span', { style: styles.drillObjective, title: detail.objective, children: detail.objective }) : null
    ] }),
    detail.status === 'failed' || detail.status === 'stale' ? jsx('div', { style: styles.drillReason, children: detail.status === 'failed'
      ? 'This run ended with at least one task failure — expand tasks below for gate chips and answers.'
      : 'This session went silent without landing a result — likely a crashed host or killed process.' }) : null,
    jsx(RunAnnotator, { api, runId, label: (detail.labels || []).length ? detail.labels[detail.labels.length - 1].label : undefined }),
    detail.revision !== undefined ? jsx('div', { style: styles.drillMeta, children: `revision ${detail.revision}` }) : null,
    detail.workspace_root ? jsx('div', { style: styles.drillMeta, title: detail.workspace_root, children: truncateMiddle(detail.workspace_root) }) : null,
    budgetsLine ? jsx('div', { style: styles.drillMeta, children: budgetsLine }) : null,
    qualityLine ? jsx('div', { style: styles.drillMeta, children: qualityLine }) : null,
    detail.receipt_count > 0 ? jsx('div', { style: styles.drillMeta, children: `${detail.receipt_count} receipt${detail.receipt_count === 1 ? '' : 's'}` }) : null,
    taskTokens > 0 ? jsx('div', { style: styles.drillMeta, children: `${compactNumber(taskTokens)} task tokens` }) : null,
    jsx(DrillDownRow, {
      id: `quality-${runId}`,
      expanded: qualityOpen,
      onToggle: () => setQualityOpen((value) => !value),
      detail: jsx(RunQualityCard, { api, runId }),
      children: jsx('span', { style: styles.drillLabel, children: 'Quality' })
    }),
    tasks.length ? jsxs('div', { style: styles.drillStack, children: [
      jsx('div', { style: styles.drillLabel, children: 'Tasks' }),
      ...tasks.map((task, index) => jsxs('div', { style: styles.listRow, children: [
        jsxs('div', { style: styles.taskRow, children: [
          jsx('span', { style: styles.listId, title: task.objective || task.id, children: task.objective || task.id || '?' }),
          jsxs('span', { style: styles.taskMeta, children: [
            jsx(StateBadge, { value: task.status }),
            Number(task.attempts) > 0 ? jsx('span', { style: styles.taskAttempts, children: `${task.attempts} attempt${Number(task.attempts) === 1 ? '' : 's'}` }) : null,
            task.gates && typeof task.gates === 'object' ? Object.entries(task.gates).slice(0, 6).map(([name, state]) => jsx('span', {
              key: name,
              title: `${name}: ${state}`,
              style: { ...styles.taskGateChip, color: state === 'ok' ? COLORS.good : state === 'failed' ? COLORS.bad : COLORS.muted },
              children: name
            }, `gate-${task.id || index}-${name}`)) : null,
            task.has_lesson ? jsxs('span', { style: styles.taskLessonChip, 'aria-label': 'Task receipt includes a lesson candidate', children: [
              jsx(Codicon, { name: 'lightbulb', size: '0.7rem' }),
              'lesson'
            ] }, `lesson-${task.id || index}`) : null,
            Number(task.tokens) > 0 ? jsx('span', { style: styles.taskAttempts, children: `${compactNumber(Number(task.tokens))} tok` }) : null
          ] })
        ] }),
        task.answer ? jsx('div', { style: { ...styles.listSecondary, whiteSpace: 'normal', lineHeight: 1.45 }, title: task.answer, children: task.answer }) : null
      ] }, `task-${task.id || index}`))
    ] }) : null,
    events.length ? jsxs('div', { style: styles.drillStack, children: [
      jsx('div', { style: styles.drillLabel, children: 'Event trail' }),
      ...trailEvents.map((event, index) => jsxs('div', { style: styles.drillStack, children: [
        jsxs('div', { style: styles.eventRow, children: [
          jsx('span', { style: styles.eventType, title: event.type, children: [
            formatStatus(event.type),
            event.task_id ? jsx('span', { style: { fontFamily: 'ui-monospace, monospace', fontSize: '11px', fontWeight: 400, color: COLORS.muted, marginLeft: '6px' }, children: event.task_id }) : null
          ] }),
          jsx('span', { style: styles.eventTime, children: formatRelativeTimestamp(event.at) })
        ] }),
        event.summary ? jsx('div', { style: { ...styles.drillMeta, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }, title: event.summary, children: event.summary }) : null
      ] }, `event-${index}`)),
      allEvents && deepEvents.isFetching && !showDeep ? jsx(Loader, { type: 'lemniscate-bloom' }) : null,
      events.length > 6 ? jsx('div', { children: jsx(Button, {
        variant: 'outline',
        size: 'sm',
        onClick: () => setAllEvents((value) => !value),
        children: allEvents ? 'Show fewer' : `Show all ${events.length} events`
      }) }) : null
    ] }) : null
  ] })
}

// Shared dismissal for dropdown menus: Escape closes, and a mousedown outside
// the ref'd container closes without swallowing that click. Dependency-free.
function useDismissable(open, onClose) {
  const containerRef = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    const onKeyDown = (event) => { if (event.key === 'Escape') onClose() }
    const onMouseDown = (event) => {
      if (containerRef.current && event.target instanceof Node && !containerRef.current.contains(event.target)) onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    document.addEventListener('mousedown', onMouseDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.removeEventListener('mousedown', onMouseDown)
    }
  }, [open, onClose])
  return containerRef
}

// --- Child status menu ------------------------------------------------------
// Compact per-child status control in the expanded campaign panel: a small
// pill button that opens a click-to-open dropdown of the most useful status
// actions (the badge itself already shows the current status). Disabled while
// a write is in flight; failures surface via the shared feedback line below
// the children list. 'Archived' is styled destructive.
const CHILD_STATUS_ACTIONS = [
  { status: 'active', label: 'Set active' },
  { status: 'blocked', label: 'Set blocked' },
  { status: 'completed', label: 'Set completed' },
  { status: 'abandoned', label: 'Set abandoned' },
  { status: 'archived', label: 'Archived', destructive: true }
]

function ChildStatusMenu({ api, campaignId, child, onResult }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const menuRef = useDismissable(open, () => setOpen(false))
  const mutation = useSipsMutation(api, {
    // useSipsMutation's string invalidateKeys cover the fleet list; the
    // campaign-scoped detail key needs the full array, invalidated explicitly.
    invalidateKeys: ['fleet'],
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['sips-control-plane', 'fleet-detail', campaignId] })
      setOpen(false)
      if (!result?.available) onResult(fleetWriteErrorText(result), true)
    },
    onError: (error) => {
      setOpen(false)
      onResult(fleetWriteErrorText(null, error), true)
    }
  })
  const busy = mutation.isPending || mutation.isLoading
  const set = (status) => {
    if (busy || status === child.status) return
    onResult(null, false)
    mutation.mutate({ path: '/fleet/child-status', body: { campaign_id: campaignId, child_id: child.child_id, status } })
  }

  return jsxs('span', { ref: menuRef, style: styles.childStatusWrap, children: [
    jsx('button', {
      type: 'button',
      'aria-label': `Status actions for ${child.title || child.child_id}`,
      'aria-expanded': open,
      disabled: busy,
      onClick: () => setOpen((value) => !value),
      style: { ...styles.childStatusBtn, ...(open ? { color: COLORS.text, borderColor: COLORS.accent } : {}) },
      children: [
        jsx(Codicon, { name: 'settings', size: '0.75rem' }),
        busy ? '…' : null
      ]
    }),
    open ? jsxs('span', { style: styles.childStatusMenu, role: 'menu', children: [
      ...CHILD_STATUS_ACTIONS.map((action) => {
        const current = action.status === child.status || (action.status === 'archived' && child.archived)
        return jsx('button', {
          type: 'button',
          role: 'menuitem',
          key: action.status,
          disabled: busy || current,
          onClick: () => set(action.status),
          style: { ...styles.childStatusOption, ...(current ? styles.childStatusOptionCurrent : {}), ...(action.destructive ? styles.childStatusOptionDanger : {}) },
          children: `${action.label}${current ? ' · current' : ''}`
        }, action.status)
      })
    ] }) : null
  ] })
}

// --- Campaign status menu ---------------------------------------------------
// Campaign-level mirror of ChildStatusMenu: a small gear pill on the FleetCard
// list rows that opens the 4 campaign statuses. The current one is marked
// '· current' and disabled; 'Archived' is styled destructive. Server-side
// transition rules decide validity — the menu always offers all 4 and surfaces
// rejection reasons via the local mapping below.
const CAMPAIGN_STATUS_ACTIONS = [
  { status: 'active', label: 'Set active' },
  { status: 'completed', label: 'Set completed' },
  { status: 'archived', label: 'Archived', destructive: true },
  { status: 'abandoned', label: 'Set abandoned' }
]

// Campaign status write rejections read as guidance, not enum text.
const CAMPAIGN_STATUS_REASON_TEXT = {
  campaign_not_found: 'This campaign no longer exists. Refresh the fleet list.',
  campaign_has_open_children: 'Complete/archive the open children first.',
  campaign_id_invalid: 'Campaign id is invalid.'
}

function campaignStatusReasonText(result, error) {
  if (error) return `Fleet write failed: ${error.message || 'unknown error'}`
  const reason = result?.reason
  const mapped = reason && CAMPAIGN_STATUS_REASON_TEXT[reason]
  if (result && result.available === false) return `Fleet write failed: ${reason?.startsWith('transition_invalid') ? 'That status change is not allowed from the current status.' : mapped || reason}`
  return `Fleet write failed: ${mapped || reason || 'unknown reason'}`
}

function CampaignStatusMenu({ api, campaign, onResult }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const menuRef = useDismissable(open, () => setOpen(false))
  const mutation = useSipsMutation(api, {
    invalidateKeys: ['fleet'],
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['sips-control-plane', 'fleet-detail', campaign.campaign_id] })
      setOpen(false)
      if (!result?.available) onResult(campaignStatusReasonText(result), true)
    },
    onError: (error) => {
      setOpen(false)
      onResult(campaignStatusReasonText(null, error), true)
    }
  })
  const busy = mutation.isPending || mutation.isLoading
  const set = (status) => {
    if (busy || status === campaign.status) return
    onResult(null, false)
    mutation.mutate({ path: '/fleet/campaign-status', body: { campaign_id: campaign.campaign_id, status } })
  }

  return jsxs('span', { ref: menuRef, style: styles.childStatusWrap, children: [
    jsx('button', {
      type: 'button',
      'aria-label': `Status actions for campaign ${campaign.campaign_id || ''}`,
      'aria-expanded': open,
      disabled: busy,
      onClick: () => setOpen((value) => !value),
      style: { ...styles.childStatusBtn, ...(open ? { color: COLORS.text, borderColor: COLORS.accent } : {}) },
      children: [
        jsx(Codicon, { name: 'settings', size: '0.75rem' }),
        busy ? '…' : null
      ]
    }),
    open ? jsxs('span', { style: styles.childStatusMenu, role: 'menu', children: [
      ...CAMPAIGN_STATUS_ACTIONS.map((action) => {
        const current = action.status === campaign.status
        return jsx('button', {
          type: 'button',
          role: 'menuitem',
          key: action.status,
          disabled: busy || current,
          onClick: () => set(action.status),
          style: { ...styles.childStatusOption, ...(current ? styles.childStatusOptionCurrent : {}), ...(action.destructive ? styles.childStatusOptionDanger : {}) },
          children: `${action.label}${current ? ' · current' : ''}`
        }, action.status)
      })
    ] }) : null
  ] })
}

function FleetDetail({ api, campaignId }) {
  const query = useQuery({
    queryKey: ['sips-control-plane', 'fleet-detail', campaignId],
    queryFn: () => api.rest(`/fleet/${encodeURIComponent(campaignId)}`),
    enabled: Boolean(campaignId),
    staleTime: 15000,
    refetchInterval: pollInterval(30000)
  })

  if (query.isLoading) {
    return jsx('div', { style: { display: 'grid', placeItems: 'center', padding: '6px 0' }, children: jsx(Loader, { type: 'lemniscate-bloom' }) })
  }
  const detail = query.data
  if (!detail?.available) {
    return jsx('div', { style: styles.drillReason, children: detail?.reason || 'Campaign detail is unavailable.' })
  }
  const children = detail.children || []
  const activity = (detail.activity || []).slice().reverse() // most recent last
  const [statusFeedback, setStatusFeedback] = useState(null)
  const [statusFeedbackError, setStatusFeedbackError] = useState(false)
  const handleStatusResult = (message, isError) => {
    setStatusFeedback(message)
    setStatusFeedbackError(Boolean(isError))
  }

  return jsxs('div', { style: styles.drillStack, children: [
    jsxs('div', { style: styles.drillHead, children: [
      jsx(StateBadge, { value: detail.status }),
      detail.status_reason ? jsx('span', { style: styles.drillMeta, title: detail.status_reason, children: formatStatus(detail.status_reason) }) : null,
      detail.objective ? jsx('span', { style: styles.drillObjective, title: detail.objective, children: detail.objective }) : null
    ] }),
    detail.revision !== undefined ? jsx('div', { style: styles.drillMeta, children: `revision ${detail.revision}` }) : null,
    detail.foreground_child_id ? jsx('div', { style: styles.drillMeta, title: detail.foreground_child_id, children: `foreground ${truncateMiddle(detail.foreground_child_id, 24)}` }) : null,
    detail.runtime_run_id || detail.workspace_root ? jsx('div', {
      style: styles.drillMeta,
      title: [detail.runtime_run_id, detail.workspace_root].filter(Boolean).join(' · '),
      children: [detail.runtime_run_id ? `run ${truncateMiddle(detail.runtime_run_id, 24)}` : null, detail.workspace_root ? truncateMiddle(detail.workspace_root) : null].filter(Boolean).join(' · ')
    }) : null,
    children.length ? jsxs('div', { style: styles.drillStack, children: [
      jsx('div', { style: styles.drillLabel, children: 'Children' }),
      ...children.map((child, index) => jsxs('div', { style: styles.childStack, children: [
        jsxs('div', { style: styles.childRow, children: [
          jsx('span', { style: styles.listId, title: child.title || child.child_id, children: child.title || child.child_id || '?' }),
          jsxs('span', { style: styles.taskMeta, children: [
            jsx(StateBadge, { value: child.status, tone: child.archived ? 'muted' : undefined }),
            Number(child.incarnation_count) > 1 ? jsx('span', { style: styles.taskAttempts, children: `×${child.incarnation_count}` }) : null,
            child.archived ? jsx(Badge, { variant: 'outline', style: styles.metaBadge, children: 'archived' }) : null,
            jsx(Badge, { variant: 'outline', style: { ...styles.metaBadge, color: COLORS.accent, borderColor: COLORS.accent }, children: child.role || 'child' }),
            jsx(ChildStatusMenu, { api, campaignId, child, onResult: handleStatusResult })
          ] })
        ] }),
        child.summary ? jsx('div', { style: { ...styles.listSecondary, whiteSpace: 'normal', lineHeight: 1.45 }, title: child.summary, children: child.summary }) : null,
        (() => {
          const meta = [child.task_id ? `task ${child.task_id}` : null, child.created_at ? `started ${formatRelativeTimestamp(child.created_at)}` : null, child.updated_at ? `updated ${formatRelativeTimestamp(child.updated_at)}` : null].filter(Boolean).join(' · ')
          return meta ? jsx('div', { style: styles.drillMeta, title: meta, children: meta }) : null
        })(),
        statusFeedback ? jsx(FleetComposerFeedback, { feedback: statusFeedback, error: statusFeedbackError }) : null
      ] }, `child-${child.child_id || index}`))
    ] }) : null,
    activity.length ? jsxs('div', { style: styles.drillStack, children: [
      jsx('div', { style: styles.drillLabel, children: 'Activity' }),
      ...activity.map((entry, index) => jsxs('div', { style: styles.eventRow, children: [
        jsxs('span', { style: styles.eventType, title: entry.detail, children: [
          formatStatus(entry.kind),
          entry.child_id ? jsx('span', { style: { ...styles.drillMeta, display: 'inline', marginLeft: '6px' }, children: entry.child_id }) : null
        ] }),
        jsx('span', { style: styles.eventTime, children: formatRelativeTimestamp(entry.at) })
      ] }, `activity-${index}`))
    ] }) : null,
    jsx(AttachChildComposer, { api, campaignId })
  ] })
}

function RunsCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'runs'], queryFn: () => api.rest('/runs'), refetchInterval: pollInterval(30000) })
  const [expandedId, setExpandedId] = useState(null)
  const toggleExpanded = (id) => setExpandedId((current) => (current === id ? null : id))

  if (query.isLoading) {
    return jsx(Card, { title: 'Session runs', icon: 'history', children: jsx('div', { style: styles.unavailable, children: 'Reading session runs…' }) })
  }
  const runs = query.data
  if (!runs?.available) {
    return jsx(Card, {
      title: 'Session runs',
      icon: 'history',
      hint: 'Backed by the sips_runtime graph run history.',
      children: jsx('div', { style: styles.unavailable, children: runs?.reason || 'No session run history yet — it appears once a session bridges to the graph runtime.' })
    })
  }

  const entries = runs.runs || []
  // Honest terminal summary: only statuses that actually have nonzero counts
  // are shown, in a fixed order, e.g. '2 succeeded · 1 failed · 2 stale'.
  const statusCounts = entries.reduce((acc, run) => {
    acc[run.status] = (acc[run.status] || 0) + 1
    return acc
  }, {})
  const statusSummary = ['succeeded', 'failed', 'stale']
    .filter((status) => statusCounts[status] > 0)
    .map((status) => `${statusCounts[status]} ${status}`)
    .join(' · ')
  return jsx(Card, {
    title: `Runs · ${compactNumber(runs.total ?? entries.length)}`,
    icon: 'history',
    hint: `${Number(runs.active) > 0 ? `${runs.active} running now · ` : ''}Most recent sessions first; click a run to expand its detail.`,
    children: entries.length ? jsxs('div', {
      children: [
        jsx('div', {
          style: styles.routeGrid,
          children: entries.map((run, index) => jsx(DrillDownRow, {
            id: run.run_id || `run-${index}`,
            expanded: expandedId === (run.run_id || `run-${index}`),
            onToggle: toggleExpanded,
            detail: jsx(RunDetail, { api, runId: run.run_id || `run-${index}` }),
            children: [
              jsx('div', { style: styles.listMain, children: [
                jsx('span', { style: styles.listId, title: run.label ? `${run.label} (${run.run_id})` : run.run_id, children: run.label ? `${run.label} · ${truncateMiddle(run.run_id || '?', 24)}` : truncateMiddle(run.run_id || '?', 24) }),
                jsxs('span', { style: styles.listMeta, children: [
                  jsx(FlipValue, { value: `${run.events ?? 0} ev`, title: `${run.events ?? 0} events`, size: '10.5px' }),
                  Number(run.receipts) > 0 ? jsx('span', { style: styles.taskAttempts, children: `${run.receipts} receipt${run.receipts === 1 ? '' : 's'}` }) : null,
                  run.progress?.total ? jsx('span', {
                    title: `${run.progress.succeeded} succeeded · ${run.progress.failed} failed · ${run.progress.active} active`,
                    style: { ...styles.value, fontVariantNumeric: 'tabular-nums', color: Number(run.progress.failed) > 0 ? COLORS.warn : COLORS.muted },
                    children: `${run.progress.succeeded}/${run.progress.total} tasks`
                  }) : null,
                  jsx(StateBadge, { value: run.status, tone: runStatusTone(run.status) }),
                  jsx('span', { style: { ...styles.eventTime, flexShrink: 0 }, children: formatRelativeTimestamp(run.updated_at) })
                ] })
              ] }),
              run.objective && run.objective !== (run.label || run.run_id) ? jsx('div', { style: run.status === 'failed' ? { ...styles.listSecondary, color: COLORS.red } : styles.listSecondary, title: run.objective, children: run.objective }) : null
            ]
          }, `run-${run.run_id || index}`))
        }),
        statusSummary ? jsx('div', { style: styles.drillMeta, children: `${statusSummary} · ${entries.length} of ${compactNumber(runs.total ?? entries.length)} shown` }) : null
      ]
    }) : jsx('div', { style: styles.unavailable, children: 'No session runs recorded yet.' })
  })
}

// Server error surfaces are already short codes ('objective_required',
// 'campaign_id_invalid', 'campaign_not_found', …). One source of truth so the
// inline feedback line renders the same shape for both composers.
function fleetWriteErrorText(result, error) {
  if (error) return `Fleet write failed: ${error.message || 'unknown error'}`
  if (result && result.available === false) return `Fleet write failed: ${result.reason || 'unknown reason'}`
  return 'Fleet write failed: unknown error'
}

// --- Fleet composers -------------------------------------------------------
// Write surface for the campaign fleet: a 'New Campaign' composer in the card
// header row and an 'Attach child' composer inside the expanded campaign
// detail. Inputs stay exactly as typed; they clear only after the server
// confirms available:true (skill contract: clear inputs only on success).

const FLEET_ROLES = ['Worker', 'Scout', 'Judge', 'Reviewer']

function FleetComposerFeedback({ feedback, error }) {
  if (!feedback) return null
  return jsx('div', { style: { ...styles.feedback, ...(error ? styles.feedbackError : {}) }, children: feedback })
}

function NewCampaignComposer({ api }) {
  const [open, setOpen] = useState(false)
  const [objective, setObjective] = useState('')
  const [campaignId, setCampaignId] = useState('')
  const [tags, setTags] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [feedbackError, setFeedbackError] = useState(false)
  const mutation = useSipsMutation(api, {
    invalidateKeys: ['fleet'],
    onSuccess: (result) => {
      if (result?.available) {
        setFeedback(`Campaign ${result.campaign_id || '(unnamed)'} created`)
        setFeedbackError(false)
        setOpen(false)
        setObjective('')
        setCampaignId('')
        setTags('')
      } else {
        setFeedback(fleetWriteErrorText(result))
        setFeedbackError(true)
      }
    },
    onError: (error) => {
      setFeedback(fleetWriteErrorText(null, error))
      setFeedbackError(true)
    }
  })
  const busy = mutation.isPending || mutation.isLoading
  const submit = () => {
    setFeedback(null)
    setFeedbackError(false)
    const body = { objective: objective.trim() }
    const trimmedId = campaignId.trim()
    if (trimmedId) body.campaign_id = trimmedId
    const tagList = tags.split(',').map((tag) => tag.trim()).filter(Boolean)
    if (tagList.length) body.tags = tagList
    mutation.mutate({ path: '/fleet/create', body })
  }

  return jsxs('div', { children: [
    jsx(Button, {
      variant: 'outline',
      size: 'sm',
      onClick: () => { setFeedback(null); setFeedbackError(false); setOpen((value) => !value) },
      children: open ? 'Cancel' : 'New Campaign'
    }),
    open ? jsxs('div', { style: { ...styles.fleetComposer, marginTop: '8px' }, children: [
      jsx('input', {
        style: { ...styles.input, width: '100%' },
        value: objective,
        placeholder: 'Objective (required)…',
        'aria-label': 'New campaign objective',
        onChange: (event) => setObjective(event.target.value),
        onKeyDown: (event) => { if (event.key === 'Enter' && objective.trim() && !busy) submit() }
      }),
      jsx('input', {
        style: { ...styles.input, width: '100%' },
        value: campaignId,
        placeholder: 'auto-generated if blank',
        'aria-label': 'New campaign id (optional)',
        onChange: (event) => setCampaignId(event.target.value),
        onKeyDown: (event) => { if (event.key === 'Enter' && objective.trim() && !busy) submit() }
      }),
      jsx('input', {
        style: { ...styles.input, width: '100%' },
        value: tags,
        placeholder: 'comma,separated,tags',
        'aria-label': 'New campaign tags (optional)',
        onChange: (event) => setTags(event.target.value),
        onKeyDown: (event) => { if (event.key === 'Enter' && objective.trim() && !busy) submit() }
      }),
      jsxs('div', { style: styles.controlRow, children: [
        jsx(Button, {
          variant: 'outline',
          size: 'sm',
          disabled: busy || !objective.trim(),
          onClick: submit,
          children: busy ? 'Creating…' : 'Create campaign'
        }),
        jsx(Button, { variant: 'ghost', size: 'sm', disabled: busy, onClick: () => setOpen(false), children: 'Cancel' })
      ] })
    ] }) : null,
    jsx(FleetComposerFeedback, { feedback: open ? null : feedback, error: feedbackError })
  ] })
}

function AttachChildComposer({ api, campaignId }) {
  const [title, setTitle] = useState('')
  const [role, setRole] = useState('Worker')
  const [objective, setObjective] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [feedbackError, setFeedbackError] = useState(false)
  const mutation = useSipsMutation(api, {
    invalidateKeys: ['fleet-detail', 'fleet'],
    onSuccess: (result) => {
      if (result?.available) {
        setFeedback(`Child "${title.trim()}" attached`)
        setFeedbackError(false)
        setTitle('')
        setRole('Worker')
        setObjective('')
      } else {
        setFeedback(fleetWriteErrorText(result))
        setFeedbackError(true)
      }
    },
    onError: (error) => {
      setFeedback(fleetWriteErrorText(null, error))
      setFeedbackError(true)
    }
  })
  const busy = mutation.isPending || mutation.isLoading
  const submit = () => {
    setFeedback(null)
    setFeedbackError(false)
    const body = { campaign_id: campaignId, title: title.trim(), role }
    const trimmedObjective = objective.trim()
    if (trimmedObjective) body.objective = trimmedObjective
    mutation.mutate({ path: '/fleet/attach', body })
  }

  return jsxs('div', { style: { ...styles.fleetComposer, marginTop: '4px' }, children: [
    jsx('div', { style: styles.drillLabel, children: 'Attach child' }),
    jsx('input', {
      style: { ...styles.input, width: '100%' },
      value: title,
      placeholder: 'Child title (required)…',
      'aria-label': 'Attach child title',
      onChange: (event) => setTitle(event.target.value),
      onKeyDown: (event) => { if (event.key === 'Enter' && title.trim() && !busy) submit() }
    }),
    jsxs('div', { style: { ...styles.controlRow, marginTop: '2px' }, children: [
      FLEET_ROLES.map((value) => jsx(Button, {
        key: value,
        variant: role === value ? 'solid' : 'outline',
        size: 'sm',
        disabled: busy,
        onClick: () => setRole(value),
        style: { minHeight: '26px', padding: '0 9px', fontSize: '12px' },
        children: value
      }))
    ] }),
    jsx('input', {
      style: { ...styles.input, width: '100%' },
      value: objective,
      placeholder: 'Objective (optional)…',
      'aria-label': 'Attach child objective',
      onChange: (event) => setObjective(event.target.value),
      onKeyDown: (event) => { if (event.key === 'Enter' && title.trim() && !busy) submit() }
    }),
    jsx(Button, {
      variant: 'outline',
      size: 'sm',
      disabled: busy || !title.trim(),
      onClick: submit,
      children: busy ? 'Attaching…' : 'Attach child'
    }),
    jsx(FleetComposerFeedback, { feedback, error: feedbackError })
  ] })
}

// --- Memory browser ---------------------------------------------------------
// Browse (not search) view over the memory fabric: tier/status toggle filters
// plus an Enter-to-submit free-text query. Rank-weighted retrieval lives in
// RecallCard; this surface only lists records. Previous data is kept while a
// refetch is in flight (placeholderData keeps the old page rendered) so the
// list does not flicker between polls.
const MEMORY_TIERS = ['work', 'knowledge', 'learning']
const MEMORY_STATUSES = ['active', 'candidate', 'archived']

function memoryBrowsePath({ tier, status, query }) {
  const params = new URLSearchParams()
  if (tier) params.set('tier', tier)
  if (status) params.set('status', status)
  const trimmed = String(query || '').trim()
  if (trimmed) params.set('query', trimmed)
  const qs = params.toString()
  return qs ? `/memory?${qs}` : '/memory'
}

function MemoryFilterGroup({ label, options, value, onChange, disabled, counts }) {
  return jsxs('span', { style: { display: 'inline-flex', alignItems: 'center', gap: '5px' }, children: [
    jsx('span', { style: styles.drillLabel, children: label }),
    jsx('span', { style: styles.memoryFilters, children: ['all', ...options].map((option) => jsx(Button, {
      key: option,
      variant: value === option ? 'solid' : 'outline',
      size: 'sm',
      disabled,
      onClick: () => onChange(option),
      title: option === 'all' ? 'Show every record' : `Show ${option} records`,
      style: { minHeight: '24px', padding: '0 9px', fontSize: '12px', fontVariantNumeric: 'tabular-nums' },
      children: option === 'all'
        ? (counts && Number(counts.__all__) > 0 ? `All · ${counts.__all__}` : 'All')
        : (counts && counts[option] !== undefined ? `${option} · ${counts[option]}` : option)
    }, option)) })
  ] })
}

function MemoryBrowser({ api }) {
  const [tier, setTier] = useState('all')
  const [status, setStatus] = useState('all')
  const [queryDraft, setQueryDraft] = useState('')
  const [query, setQuery] = useState('')
  const memoryQuery = useQuery({
    queryKey: ['sips-control-plane', 'memory', tier, status, query],
    queryFn: () => api.rest(memoryBrowsePath({ tier, status, query })),
    placeholderData: (previous) => previous,
    refetchInterval: pollInterval(60000)
  })

  if (memoryQuery.isLoading) {
    return jsx(Card, { title: 'Memory', icon: 'database', children: jsx('div', { style: styles.unavailable, children: 'Reading the memory fabric…' }) })
  }
  const memory = memoryQuery.data
  if (!memory?.available) {
    return jsx(Card, {
      title: 'Memory',
      icon: 'database',
      hint: 'Browse the SIPS memory fabric; ranked retrieval lives in the recall card.',
      children: jsx('div', { style: styles.unavailable, children: memory?.reason || 'Memory fabric is unavailable.' })
    })
  }

  const records = memory.records || []
  const totalRecords = Number(memory.total_records) || 0
  const totalMatched = Number(memory.total_matched) || 0
  const filtersActive = tier !== 'all' || status !== 'all' || Boolean(query.trim())
  // Filter-button counts come from the backend's full-store tallies, so each
  // toggle shows how many records it would select before it is clicked.
  const tierCounts = memory.tier_counts || {}
  const statusCounts = memory.status_counts || {}
  const submitQuery = () => setQuery(queryDraft.trim())

  return jsx(Card, {
    title: `Memory · ${compactNumber(totalRecords)}`,
    icon: 'database',
    hint: memory.claim_boundary || 'Browse the SIPS memory fabric; ranked retrieval lives in the recall card.',
    children: [
      jsxs('div', { style: styles.memoryFilters, children: [
        jsx(MemoryFilterGroup, { label: 'Tier', options: MEMORY_TIERS, value: tier, onChange: setTier, disabled: memoryQuery.isFetching && !memoryQuery.isLoading, counts: { ...tierCounts, __all__: totalRecords } }),
        jsx(MemoryFilterGroup, { label: 'Status', options: MEMORY_STATUSES, value: status, onChange: setStatus, disabled: memoryQuery.isFetching && !memoryQuery.isLoading, counts: { ...statusCounts, __all__: totalRecords } }),
        jsx('input', {
          style: styles.input,
          value: queryDraft,
          placeholder: 'Filter by text (Enter)…',
          'aria-label': 'Memory browse query',
          onChange: (event) => setQueryDraft(event.target.value),
          onKeyDown: (event) => { if (event.key === 'Enter') submitQuery() }
        })
      ] }),
      records.length ? jsxs('div', { style: { marginTop: '8px' }, children: [
        records.map((record, index) => jsxs('div', { style: styles.listRow, children: [
          jsxs('div', { style: styles.listMain, children: [
            jsx('span', { style: styles.listId, title: record.title, children: record.title || record.id || '?' }),
            jsxs('span', { style: styles.listMeta, children: [
              jsx(StateBadge, { value: record.tier }),
              jsx(StateBadge, { value: record.status, tone: record.status === 'active' ? 'good' : record.status === 'archived' ? 'muted' : 'warn' }),
              jsx('span', { style: styles.eventTime, children: formatRelativeTimestamp(record.created_at) })
            ] })
          ] }),
          record.preview ? jsx('div', { style: styles.listSecondary, title: record.preview, children: record.preview }) : null
        ] }, `memory-${record.id || index}`))
      ] }) : jsx('div', { style: { ...styles.unavailable, marginTop: '8px' }, children: filtersActive ? 'No records match the current filters.' : 'The memory fabric has no records yet.' }),
      filtersActive ? jsx('div', { style: styles.memoryMatched, children: `matched ${compactNumber(totalMatched)} of ${compactNumber(totalRecords)}` }) : null,
      memoryQuery.isFetching && !memoryQuery.isLoading ? jsx('div', { style: { ...styles.memoryMatched, marginTop: '2px' }, children: 'Refreshing…' }) : null
    ]
  })
}

function FleetCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'fleet'], queryFn: () => api.rest('/fleet'), refetchInterval: pollInterval(30000) })
  const [expandedId, setExpandedId] = useState(null)
  const [statusFeedback, setStatusFeedback] = useState(null)
  const [statusFeedbackError, setStatusFeedbackError] = useState(false)
  const handleStatusResult = (message, isError) => {
    setStatusFeedback(message)
    setStatusFeedbackError(Boolean(isError))
  }
  const toggleExpanded = (id) => setExpandedId((current) => (current === id ? null : id))

  if (query.isLoading) {
    return jsx(Card, { title: 'Campaign fleet', icon: 'layers', children: jsx('div', { style: styles.unavailable, children: 'Reading campaign fleet…' }) })
  }
  const fleet = query.data
  if (!fleet?.available) {
    return jsx(Card, {
      title: 'Campaign fleet',
      icon: 'layers',
      hint: 'Backed by campaign fleet spines in the graph runtime.',
      children: jsx('div', { style: styles.unavailable, children: fleet?.reason || 'Campaign fleet is unavailable.' })
    })
  }

  const campaigns = fleet.campaigns || []
  return jsx(Card, {
    title: `Fleet · ${compactNumber(fleet.total ?? campaigns.length)}`,
    icon: 'layers',
    hint: 'Campaign spines and their child threads; click a campaign to expand its detail.',
    actions: jsx(NewCampaignComposer, { api }),
    children: jsx('div', {
      style: styles.routeGrid,
      children: campaigns.length ? campaigns.map((campaign, index) => jsx(DrillDownRow, {
        id: campaign.campaign_id || `campaign-${index}`,
        expanded: expandedId === (campaign.campaign_id || `campaign-${index}`),
        onToggle: toggleExpanded,
        detail: jsx(FleetDetail, { api, campaignId: campaign.campaign_id || `campaign-${index}` }),
        children: [
          jsx('div', { style: styles.listMain, children: [
            jsx('span', { style: styles.listId, title: campaign.campaign_id, children: campaign.campaign_id || '?' }),
            jsxs('span', { style: styles.listMeta, children: [
              jsx('span', { style: { ...styles.value, fontVariantNumeric: 'tabular-nums' }, children: [
                `${campaign.child_count ?? 0} child${Number(campaign.child_count) === 1 ? '' : 'ren'}`,
                Number(campaign.archived_child_count) > 0 ? ` · ${campaign.archived_child_count} archived` : null
              ] }),
              jsx(StateBadge, { value: campaign.status }),
              jsx(CampaignStatusMenu, { api, campaign, onResult: handleStatusResult })
            ] })
          ] }),
          campaign.objective ? jsx('div', { style: styles.listSecondary, title: campaign.objective, children: campaign.objective }) : null,
          (campaign.tags || []).length ? jsx('div', { style: styles.listTags, children: campaign.tags.map((tag) => jsx(Badge, { key: tag, variant: 'outline', style: styles.metaBadge, children: tag })) }) : null,
          statusFeedback ? jsx(FleetComposerFeedback, { feedback: statusFeedback, error: statusFeedbackError }) : null
        ]
      }, `campaign-${campaign.campaign_id || index}`)) : jsx('div', { style: styles.unavailable, children: 'No campaigns yet — create one with New Campaign above, or wait for fleet spines to appear.' })
    })
  })
}

// Tool-call lens: per-tool call volume from GET /lifecycle, one segmented bar
// per tool (ok in good, error/denied in bad, other in muted) sized relative to
// the busiest tool. Metadata only — mirrors LifecycleCard's data source.
function ToolCallsCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'lifecycle'], queryFn: () => api.rest('/lifecycle'), refetchInterval: pollInterval(30000) })
  const title = 'Tool call volume'
  const icon = 'tools'

  if (query.isLoading) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'Reading tool usage…' }) })
  }
  if (query.isError) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'The lifecycle endpoint is unavailable right now. Retry from the header refresh.' }) })
  }
  const lifecycle = query.data
  if (!lifecycle?.available) {
    return jsx(Card, {
      title,
      icon,
      hint: 'Backed by the agent hook stream.',
      children: jsx('div', { style: styles.unavailable, children: 'No tool-call data is available yet — it fills as the SIPS lifecycle hooks observe tool calls.' })
    })
  }

  const tools = (lifecycle.tools || []).slice().sort((a, b) => (Number(b.total) || 0) - (Number(a.total) || 0)).slice(0, 6)
  const maxTool = Math.max(...tools.map((row) => Number(row.total) || 0), 1)
  const seg = (count) => `${(Number(count) || 0) / maxTool * 100}%`

  return jsx(Card, {
    title,
    icon,
    hint: `${compactNumber(lifecycle.window_events || 0)} events in window · top ${tools.length || 0} of ${compactNumber((lifecycle.tools || []).length)}`,
    children: tools.length ? jsx('div', { style: { display: 'grid', gap: '9px' }, children: tools.map((row) => {
      const total = Number(row.total) || 0
      const issues = (Number(row.error) || 0) + (Number(row.denied) || 0)
      return jsxs('div', {
        children: [
          jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px', marginBottom: '4px' }, children: [
            jsx('span', { style: { fontSize: '12px', fontWeight: 650, fontFamily: 'ui-monospace, monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: [
              jsx('span', { 'aria-hidden': true, style: { marginRight: '6px', flexShrink: 0 }, children: toolIcon(row.tool) }),
              row.tool || 'unknown tool'
            ] }),
            jsxs('span', { style: { flexShrink: 0, fontSize: '11px', fontVariantNumeric: 'tabular-nums' }, children: [
              jsx('span', { style: { color: COLORS.text, fontWeight: 650 }, children: compactNumber(total) }),
              issues ? jsx('span', { style: { color: COLORS.warn }, children: ` · ${issues} issue${issues === 1 ? '' : 's'}` }) : null
            ] })
          ] }),
          jsx('div', {
            style: { display: 'flex', height: '7px', borderRadius: '999px', overflow: 'hidden', background: 'rgba(255,255,255,0.08)' },
            role: 'img',
            'aria-label': `${row.tool}: ${total} calls, ${issues} with issues`,
            children: [
              jsx('div', { key: 'ok', style: { width: seg(row.ok), background: COLORS.good } }),
              jsx('div', { key: 'issues', style: { width: seg(issues), background: COLORS.bad } }),
              jsx('div', { key: 'other', style: { width: seg(row.other), background: COLORS.muted, opacity: 0.5 } })
            ]
          })
        ]
      }, `toolvol-${row.tool || 'unknown'}`)
    }) }) : jsx('div', { style: styles.unavailable, children: 'No tool calls observed in the current window.' })
  })
}

// Hook-flow lens: the event-type mix over the most recent events, one
// max-scaled bar per event type present, ordered by count descending.
// Per-tool icons + per-event-type icons, shared by ToolCallsCard, HookFlowCard
// and the chat cards (sips_chat_cards.py mirrors the tool map). One lookup for
// exact names, then prefix rules for MCP/wrapper variants; fallback '⚙'.
const TOOL_ICONS = {
  terminal: '❯',
  read_file: '📖',
  write_file: '✍️',
  patch: '🔧',
  search_files: '🔎',
  execute_code: '🐍',
  vision_analyze: '👁',
  skill_view: '📚',
  skill_manage: '🛠',
  skills_list: '📋',
  session_search: '🧭',
  memory: '🧠',
  delegate_task: '🚀',
  process: '⏯',
  todo: '☑',
  clarify: '❓',
  web_search: '🌐',
  web_extract: '📰',
  browser_exec: '🌍',
  browser: '🌍',
  image_generate: '🎨',
  cronjob: '⏰',
  tour: '🧭',
  tip: '💡',
  setup_mcp: '🔌'
}

const TOOL_ICON_PREFIXES = [
  [/^mcp__/, '🔌'],
  [/^codex-/, '🧩']
]

function toolIcon(name) {
  const key = String(name || '').trim()
  if (TOOL_ICONS[key]) return TOOL_ICONS[key]
  for (const [pattern, icon] of TOOL_ICON_PREFIXES) {
    if (pattern.test(key)) return icon
  }
  return '⚙'
}

const HOOK_EVENT_ICONS = [
  [/^pre_tool_call/, '⏳'],
  [/^post_tool_call/, '⏱'],
  [/^pre_llm_call/, '🧮'],
  [/^on_skill/, '📚'],
  [/^on_session_start/, '▶'],
  [/^on_session_end_record/, '💾'],
  [/^on_session_end/, '⏹'],
  [/^on_session_reset/, '⟳'],
  [/^subagent_start/, '🚀'],
  [/^subagent_stop/, '🛬'],
  [/^subagent/, '◈']
]
function hookEventIcon(type) {
  const match = HOOK_EVENT_ICONS.find(([pattern]) => pattern.test(type))
  return match ? match[1] : '·'
}
// Tone per hook event family: pre-calls are intent (muted), post-calls are
// outcomes (accent), failures surface in red via the outcome mix.
function hookEventBarColor(type) {
  if (/^pre_/.test(type)) return COLORS.muted
  if (/error|denied|blocked|fail/.test(type)) return COLORS.bad
  return COLORS.accent
}

function HookFlowCard({ events }) {
  const recent = (events?.recent || []).slice(0, 40)
  if (!events?.available || !recent.length) {
    return jsx(Card, { title: 'Hook flow', icon: 'symbol-event', children: jsx('div', { style: styles.unavailable, children: 'No lifecycle events are available yet.' }) })
  }

  const tally = new Map()
  for (const entry of recent) {
    const type = entry.event || 'unknown'
    tally.set(type, (tally.get(type) || 0) + 1)
  }
  const rows = [...tally.entries()].sort((a, b) => b[1] - a[1])
  const maxCount = Math.max(...rows.map(([, count]) => count), 1)

  return jsx(Card, {
    title: 'Hook flow',
    icon: 'symbol-event',
    hint: `Event mix over the last ${compactNumber(recent.length)} of ${compactNumber(events.event_count || 0)} recorded events`,
    children: [
      jsx('div', { style: { display: 'grid', gap: '9px' }, children: rows.map(([type, count]) => jsxs('div', {
        children: [
          jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px', marginBottom: '4px' }, children: [
            jsxs('span', { style: { display: 'inline-flex', alignItems: 'baseline', gap: '6px', minWidth: 0, fontSize: '12px', fontWeight: 650 }, children: [
              hookEventIcon(type) ? jsx('span', { 'aria-hidden': true, style: { color: COLORS.muted, flexShrink: 0 }, children: hookEventIcon(type) }) : null,
              jsx('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: formatStatus(type) })
            ] }),
            jsx('span', { style: { flexShrink: 0, color: COLORS.muted, fontSize: '11px', fontVariantNumeric: 'tabular-nums' }, children: compactNumber(count) })
          ] }),
          jsx('div', {
            style: { height: '5px', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' },
            role: 'img',
            'aria-label': `${type}: ${count} events`,
            children: jsx('div', { style: { height: '100%', width: `${count / maxCount * 100}%`, borderRadius: '999px', background: hookEventBarColor(type), opacity: 0.75 } })
          })
        ]
      }, `hookflow-${type}`)) }),
      events.recent_capped ? jsx('div', {
        style: { ...styles.eventCapNote, textAlign: 'left', margin: '10px 0 0' },
        children: `Showing the most recent ${compactNumber(recent.length)} of ${compactNumber(events.event_count || 0)} recorded events.`
      }) : null
    ]
  })
}

// Token-usage lens: aggregate token analytics from the Hermes session store
// via /token-usage. Totals row, daily cache-hit trend, and the replay leaders
// (tool results whose size x later-calls dominates context burn).
function formatTokens(value) {
  const n = Number(value) || 0
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return String(n)
}

function TokenUsageCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'token-usage'], queryFn: () => api.rest('/token-usage'), refetchInterval: pollInterval(60000) })
  const title = 'Token usage'
  const icon = 'pulse'

  if (query.isLoading) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'Reading session store…' }) })
  }
  if (query.isError || !query.data?.available) {
    return jsx(Card, {
      title,
      icon,
      hint: 'Read-only aggregate over ~/.hermes/state.db.',
      children: jsx('div', { style: styles.unavailable, children: query.data?.reason || 'The session store is unavailable right now.' })
    })
  }

  const data = query.data
  const totals = data.totals || {}
  const replay = data.replay || {}
  const split = data.direct_vs_subagent || {}
  const daily = (data.daily || []).slice(-7)
  const maxFresh = Math.max(...daily.map((row) => Number(row.fresh_input_tokens) || 0), 1)

  const subFresh = Number(split.subagent?.fresh_input_tokens) || 0
  const directFresh = Number(split.direct?.fresh_input_tokens) || 0
  const freshShare = subFresh + directFresh ? Math.round(subFresh / (subFresh + directFresh) * 100) : 0

  return jsx(Card, {
    title,
    icon,
    hint: `${data.window_days}-day window · read-only aggregate, no message content`,
    children: [
      jsx('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '12px' }, children: [
        jsxs('div', { children: [
          jsx('div', { style: { fontSize: '17px', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }, children: formatTokens(totals.fresh_input_tokens) }),
          jsx('div', { style: { ...styles.label, fontSize: '10px' }, children: 'fresh input' })
        ] }, 'tk-fresh'),
        jsxs('div', { children: [
          jsx('div', { style: { fontSize: '17px', fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: COLORS.accent }, children: `${totals.cache_hit_pct ?? '—'}%` }),
          jsx('div', { style: { ...styles.label, fontSize: '10px' }, children: 'cache hit' })
        ] }, 'tk-hit'),
        jsxs('div', { children: [
          jsx('div', { style: { fontSize: '17px', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }, children: formatTokens(totals.output_tokens) }),
          jsx('div', { style: { ...styles.label, fontSize: '10px' }, children: `output · ${totals.fresh_to_output_ratio || '—'}` })
        ] }, 'tk-out')
      ] }, 'tk-totals'),
      daily.length ? jsx('div', { style: { display: 'grid', gap: '6px', marginBottom: '12px' }, children: daily.map((row) => jsxs('div', {
        children: [
          jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px', marginBottom: '3px' }, children: [
            jsx('span', { style: { fontSize: '11px', fontFamily: 'ui-monospace, monospace', color: COLORS.muted }, children: row.day?.slice(5) || row.day }),
            jsxs('span', { style: { fontSize: '11px', fontVariantNumeric: 'tabular-nums' }, children: [
              jsx('span', { style: { fontWeight: 650 }, children: formatTokens(row.fresh_input_tokens) }),
              jsx('span', { style: { color: Number(row.cache_hit_pct) >= 90 ? COLORS.good : COLORS.warn }, children: ` · ${row.cache_hit_pct ?? '—'}% cached` })
            ] })
          ] }),
          jsx('div', { style: { height: '5px', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }, role: 'img', 'aria-label': `${row.day}: ${row.fresh_input_tokens} fresh input tokens, ${row.cache_hit_pct}% cache hit`, children: jsx('div', { style: { height: '100%', width: `${(Number(row.fresh_input_tokens) || 0) / maxFresh * 100}%`, borderRadius: '999px', background: COLORS.accent, opacity: 0.7 } }) })
        ]
      }, `tkd-${row.day}`)) }) : null,
      replay.tool_results_replayed_tokens_est ? jsx('div', { style: { display: 'grid', gap: '5px' }, children: [
        jsx('div', { style: { ...styles.label, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em' }, children: `Replay leaders · ~${formatTokens(replay.tool_results_replayed_tokens_est)} replayed from tool results` }),
        (replay.top_tools || []).slice(0, 4).map((row) => jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }, children: [
          jsx('span', { style: { fontSize: '11px', fontFamily: 'ui-monospace, monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: row.tool }),
          jsx('span', { style: { flexShrink: 0, fontSize: '11px', fontVariantNumeric: 'tabular-nums', color: COLORS.muted }, children: `~${formatTokens(row.replayed_tokens_est)}` })
        ] }, `tkt-${row.tool}`)),
        (replay.top_sessions || []).length ? jsx('div', { style: { ...styles.label, fontSize: '10px', marginTop: '4px' }, children: `heaviest session: ${replay.top_sessions[0].session_id} (~${formatTokens(replay.top_sessions[0].replayed_tool_tokens_est)})` }) : null
      ] }) : null,
      subFresh || directFresh ? jsx('div', { style: { ...styles.label, fontSize: '10px', marginTop: '10px' }, children: `Subagents took ${freshShare}% of fresh input (${formatTokens(subFresh)} of ${formatTokens(subFresh + directFresh)})` }) : null
    ]
  })
}

// Context-scan lens: oversized files that dominate context burn, from
// /context-scan (homebase.context_scan.v1). One max-scaled bar per risk
// ordered heaviest first, tone dot by estimated tokens (red >25K, yellow
// >10K, green else), plus the bounded_read command that inspects each file
// without reopening the whole thing into context.
function contextTone(tokens) {
  const n = Number(tokens) || 0
  if (n > 25000) return COLORS.bad
  if (n > 10000) return COLORS.warn
  return COLORS.good
}

function ContextScanCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'context-scan'], queryFn: () => api.rest('/context-scan'), refetchInterval: pollInterval(60000) })
  const title = 'Context scan'
  const icon = 'eye'

  if (query.isLoading) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'Scanning oversized files…' }) })
  }
  if (query.isError || !query.data?.available) {
    return jsx(Card, {
      title,
      icon,
      hint: 'Bounded scan of files that threaten the context budget.',
      children: jsx('div', { style: styles.unavailable, children: query.data?.claim_boundary || 'The context-scan endpoint is unavailable right now.' })
    })
  }

  const data = query.data
  const risks = (data.risks || []).slice().sort((a, b) => (Number(b.estimated_tokens) || 0) - (Number(a.estimated_tokens) || 0))
  const maxTokens = Math.max(...risks.map((row) => Number(row.estimated_tokens) || 0), 1)
  const shown = risks.length
  const total = Number(data.risk_count) || shown

  return jsx(Card, {
    title,
    icon,
    hint: shown
      ? `${compactNumber(total)} file${total === 1 ? '' : 's'} over the ${formatTokens(data.max_bytes)}-byte line · heaviest ${shown} shown`
      : `${compactNumber(total)} file${total === 1 ? '' : 's'} over the ${formatTokens(data.max_bytes)}-byte line`,
    children: risks.length ? jsx('div', { style: { display: 'grid', gap: '9px' }, children: risks.map((row) => {
      const tokens = Number(row.estimated_tokens) || 0
      const bytes = Number(row.bytes) || 0
      const tone = contextTone(tokens)
      const read = String(row.bounded_read || '')
      return jsxs('div', {
        children: [
          jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px', marginBottom: '4px', flexWrap: 'wrap' }, children: [
            jsxs('span', { title: row.path, style: { display: 'inline-flex', alignItems: 'center', minWidth: 0, flex: '1 1 200px', fontSize: '11.5px', fontWeight: 650, fontFamily: MONO, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: [
              jsx('span', { 'aria-hidden': true, style: { flexShrink: 0, width: '7px', height: '7px', borderRadius: '999px', background: tone, marginRight: '6px' } }),
              row.path || 'unknown path'
            ] }),
            jsxs('span', { style: { flexShrink: 0, fontSize: '11px', fontVariantNumeric: 'tabular-nums' }, children: [
              jsx('span', { style: { color: COLORS.muted }, children: `${compactNumber(bytes)}B` }),
              jsx('span', { style: { color: tone, fontWeight: 650 }, children: ` · ~${formatTokens(tokens)} tok` })
            ] })
          ] }),
          jsx('div', {
            style: { height: '5px', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' },
            role: 'img',
            'aria-label': `${row.path}: ~${tokens} estimated tokens, ${bytes} bytes`,
            children: jsx('div', { style: { height: '100%', width: `${tokens / maxTokens * 100}%`, borderRadius: '999px', background: tone, opacity: 0.75 } })
          }),
          read ? jsx('div', { title: read, style: { marginTop: '3px', fontSize: '11px', fontFamily: 'ui-monospace, monospace', color: COLORS.muted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: read }) : null
        ]
      }, `ctxscan-${row.path || 'unknown'}`)
    }) }) : jsx('div', { style: styles.unavailable, children: 'Context is clean' })
  })
}

// Tool-latency lens: bounded duration aggregates from the hook stream via
// /tool-latency (sips.tool-latency.v1). One max-scaled bar per tool ordered by
// total_ms descending, median/p90/max in compact form. Durations only started
// recording recently, so tools with calls but no timed calls yet render as
// muted 'awaiting timings' rows at the bottom.
function formatMs(value) {
  const n = Number(value) || 0
  if (n >= 60000) return `${(n / 60000).toFixed(1)}m`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}s`
  return `${Math.round(n)}ms`
}

function ToolLatencyCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'tool-latency'], queryFn: () => api.rest('/tool-latency'), refetchInterval: pollInterval(45000) })
  const title = 'Tool latency'
  const icon = 'pulse'

  if (query.isLoading) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'Reading tool latency…' }) })
  }
  if (query.isError || !query.data?.available) {
    return jsx(Card, {
      title,
      icon,
      hint: 'Backed by the agent hook stream.',
      children: jsx('div', { style: styles.unavailable, children: query.data?.reason || 'The tool-latency endpoint is unavailable right now.' })
    })
  }

  const data = query.data
  const timedMs = (row) => {
    if (row.total_ms != null) return Number(row.total_ms) || 0
    return (Number(row.total_s) || 0) * 1000
  }
  const timedCalls = (row) => {
    const n = Number(row.timed_calls)
    if (Number.isFinite(n)) return n
    return row.median_ms != null ? (Number(row.calls) || 0) : 0
  }
  const all = (data.tools || []).slice().sort((a, b) => timedMs(b) - timedMs(a))
  const timed = all.filter((row) => timedCalls(row) > 0 && timedMs(row) > 0)
  const awaiting = all.filter((row) => timedCalls(row) === 0 && (Number(row.calls) || 0) > 0).slice(0, 3)

  if (!all.length) {
    return jsx(Card, {
      title,
      icon,
      hint: `${data.window_hours}h window · read-only duration aggregate, no tool arguments or outputs`,
      children: jsx('div', { style: styles.unavailable, children: 'No tool calls observed in the current window.' })
    })
  }

  const totalTimed = Number(data.timed_calls) || timed.reduce((sum, row) => sum + timedCalls(row), 0)
  const maxMs = Math.max(...timed.map(timedMs), 1)

  return jsx(Card, {
    title,
    icon,
    hint: `${compactNumber(totalTimed)} timed calls · ${data.window_hours}h window`,
    children: [
      jsx('div', { style: { display: 'grid', gap: '9px' }, children: timed.map((row) => {
        const ms = timedMs(row)
        const errors = Number(row.error_count) || 0
        return jsxs('div', {
          children: [
            jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px', marginBottom: '4px' }, children: [
              jsxs('span', { style: { fontSize: '12px', fontWeight: 650, fontFamily: 'ui-monospace, monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: [
                jsx('span', { 'aria-hidden': true, style: { marginRight: '6px', flexShrink: 0 }, children: toolIcon(row.tool) }),
                row.tool || 'unknown tool'
              ] }),
              jsxs('span', { style: { flexShrink: 0, fontSize: '11px', fontVariantNumeric: 'tabular-nums' }, children: [
                jsx('span', { style: { color: COLORS.text, fontWeight: 650 }, children: formatMs(row.median_ms) }),
                jsx('span', { style: { color: COLORS.muted }, children: ` · ${formatMs(row.p90_ms)} · ${formatMs(row.max_ms)}` }),
                errors ? jsx('span', { style: { color: COLORS.warn }, children: ` · ${errors} err` }) : null
              ] })
            ] }),
            jsx('div', {
              style: { height: '7px', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' },
              role: 'img',
              'aria-label': `${row.tool}: median ${formatMs(row.median_ms)}, p90 ${formatMs(row.p90_ms)}, max ${formatMs(row.max_ms)} across ${timedCalls(row)} timed calls`,
              children: jsx('div', { style: { height: '100%', width: `${ms / maxMs * 100}%`, borderRadius: '999px', background: COLORS.accent, opacity: 0.75 } })
            })
          ]
        }, `toollat-${row.tool || 'unknown'}`)
      }) }),
      awaiting.length ? jsx('div', { style: { display: 'grid', gap: '5px', marginTop: timed.length ? '10px' : undefined }, children: awaiting.map((row) => jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }, children: [
        jsxs('span', { style: { fontSize: '11px', fontFamily: 'ui-monospace, monospace', color: COLORS.muted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: [
          jsx('span', { 'aria-hidden': true, style: { marginRight: '6px', flexShrink: 0 }, children: toolIcon(row.tool) }),
          row.tool || 'unknown tool'
        ] }),
        jsx('span', { style: { flexShrink: 0, fontSize: '11px', color: COLORS.muted }, children: 'awaiting timings' })
      ] }, `toollatwait-${row.tool || 'unknown'}`)) }) : null,
      !timed.length ? jsx('div', { style: { ...styles.label, fontSize: '10px', marginTop: '8px' }, children: 'No durations recorded yet — timings appear as the hook stream fills.' }) : null
    ]
  })
}

// Timeline lens: the most recent runs and campaigns from GET /timeline as a
// vertical time axis. One status-colored row per entry: glyph, truncated id,
// relative timestamp, and the event count (runs) or children count (campaigns).
// Bounds to 12 rows with a muted overflow note so the card stays scannable.
function TimelineCard({ api }) {
  const query = useQuery({ queryKey: ['sips', 'timeline'], queryFn: () => api.rest('/timeline'), refetchInterval: pollInterval(30000) })
  const title = 'Timeline'
  const icon = 'history'

  if (query.isLoading) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'Reading the timeline…' }) })
  }
  if (query.isError) {
    return jsx(Card, {
      title,
      icon,
      hint: 'Backed by the run and campaign ledger.',
      children: jsx('div', { style: styles.unavailable, children: 'The timeline endpoint is unavailable right now. Retry from the header refresh.' })
    })
  }

  const entries = Array.isArray(query.data?.entries) ? query.data.entries : []
  if (!query.data?.available || !entries.length) {
    return jsx(Card, {
      title,
      icon,
      hint: 'Backed by the run and campaign ledger.',
      children: jsx('div', { style: styles.unavailable, children: 'No timeline entries yet.' })
    })
  }

  const glyphFor = (entry) => entry.kind === 'campaign' ? '◇' : entry.status === 'succeeded' ? '✓' : entry.status === 'failed' ? '✗' : '◐'
  const toneKeyFor = (entry) => {
    if (entry.kind === 'campaign') return 'muted'
    if (entry.status === 'succeeded') return 'good'
    if (entry.status === 'failed') return 'bad'
    if (entry.status === 'stale') return 'warn'
    return 'accent'
  }

  const visible = entries.slice(0, 12)
  const olderCount = entries.length - visible.length

  return jsx(Card, {
    title,
    icon,
    hint: `${compactNumber(entries.length)} recent entries · runs and campaigns`,
    children: [
      jsx('div', { style: { display: 'grid', gap: '7px' }, children: visible.map((entry) => {
        const color = COLORS[toneKeyFor(entry)] || COLORS.muted
        const countLabel = entry.kind === 'campaign' ? `${compactNumber(entry.children)} children` : `${compactNumber(entry.events)} events`
        return jsxs('div', {
          style: { display: 'flex', alignItems: 'baseline', gap: '8px', minWidth: 0 },
          children: [
            jsx('span', { 'aria-hidden': true, style: { color, flexShrink: 0, width: '12px', textAlign: 'center' }, children: glyphFor(entry) }),
            jsx('span', { title: entry.id, style: { color, fontFamily: 'ui-monospace, monospace', fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: String(entry.id || '?').slice(0, 24) }),
            jsx('span', { style: { flexShrink: 0, marginLeft: 'auto', color: COLORS.steelDim, fontSize: '11px', fontFamily: MONO }, children: formatRelativeTimestamp(entry.ts ? entry.ts * 1000 : null) }),
            jsx(FlipValue, { value: countLabel, size: '10.5px' })
          ]
        }, `timeline-${entry.kind || 'run'}-${entry.id}`)
      }) }),
      olderCount > 0 ? jsx('div', { style: { color: COLORS.muted, fontSize: '11px', marginTop: '8px' }, children: `…${compactNumber(olderCount)} older` }) : null
    ]
  })
}

// Verdict lens: per-tool call outcomes from GET /verdicts?window_hours=N.
// One row per tool: icon, truncated name, call count, a verdict pill colored
// ok->good / slow->warn / stalled->bad / denied->bad, and p95/median durations
// via formatMs. Backend sorts worst-first, so payload order is preserved.
// /tool-latency carries aggregates only (no per-event rows), so instead of a
// drill-down the card offers a window_hours selector (1h/6h/24h/7d); the
// window is part of the useQuery key so each cadence caches separately.
const VERDICT_TONE = { ok: 'good', slow: 'warn', stalled: 'bad', denied: 'bad' }
const VERDICT_WINDOWS = [
  { label: '1h', hours: 1 },
  { label: '6h', hours: 6 },
  { label: '24h', hours: 24 },
  { label: '7d', hours: 168 }
]

// Segmented window selector rendered in the card title row (Card `actions`).
function verdictWindowSelector(windowHours, setWindowHours) {
  return jsx('div', { style: styles.segRow, role: 'group', 'aria-label': 'Verdict window', children: VERDICT_WINDOWS.map((option) => jsxs('button', {
    type: 'button',
    'aria-pressed': windowHours === option.hours,
    onClick: () => setWindowHours(option.hours),
    style: { ...styles.segBtn, ...(windowHours === option.hours ? styles.segBtnActive : {}) },
    children: option.label
  }, `verdict-window-${option.label}`)) })
}

function VerdictsCard({ api }) {
  const [windowHours, setWindowHours] = useState(24)
  const query = useQuery({ queryKey: ['sips', 'verdicts', windowHours], queryFn: () => api.rest(`/verdicts?window_hours=${windowHours}`), refetchInterval: pollInterval(45000) })
  const title = 'Tool verdicts'
  const icon = 'checklist'
  const windowLabel = (VERDICT_WINDOWS.find((option) => option.hours === windowHours) || {}).label || `${windowHours}h`

  if (query.isLoading) {
    return jsx(Card, { title, icon, actions: verdictWindowSelector(windowHours, setWindowHours), children: jsx('div', { style: styles.unavailable, children: 'Reading tool verdicts…' }) })
  }
  if (query.isError) {
    return jsx(Card, {
      title,
      icon,
      actions: verdictWindowSelector(windowHours, setWindowHours),
      hint: 'Backed by the agent hook stream.',
      children: jsx('div', { style: styles.unavailable, children: 'The verdicts endpoint is unavailable right now. Retry from the header refresh.' })
    })
  }

  const verdicts = Array.isArray(query.data?.verdicts) ? query.data.verdicts : []
  if (!query.data?.available || !verdicts.length) {
    return jsx(Card, {
      title,
      icon,
      actions: verdictWindowSelector(windowHours, setWindowHours),
      hint: 'Backed by the agent hook stream.',
      children: jsx('div', { style: styles.unavailable, children: `No tool calls in the ${windowLabel} window yet.` })
    })
  }

  return jsx(Card, {
    title,
    icon,
    actions: verdictWindowSelector(windowHours, setWindowHours),
    hint: `${compactNumber(verdicts.length)} tool${verdicts.length === 1 ? '' : 's'} · ${windowLabel} window · worst first`,
    children: jsx('div', { style: { display: 'grid', gap: '7px' }, children: verdicts.map((entry) => {
      const pillColor = COLORS[VERDICT_TONE[entry.verdict]] || COLORS.muted
      const denials = Number(entry.denials) || 0
      return jsxs('div', {
        style: { display: 'flex', alignItems: 'baseline', gap: '8px', minWidth: 0 },
        children: [
          jsxs('span', { title: entry.tool, style: { display: 'inline-flex', alignItems: 'baseline', gap: '6px', minWidth: 0, flexShrink: 1, overflow: 'hidden' }, children: [
            jsx('span', { 'aria-hidden': true, style: { flexShrink: 0 }, children: toolIcon(entry.tool) }),
            jsx('span', { style: { fontFamily: 'ui-monospace, monospace', fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: String(entry.tool || 'unknown tool').slice(0, 24) })
          ] }),
          jsx('span', { style: { flexShrink: 0, color: COLORS.muted, fontSize: '11px', fontVariantNumeric: 'tabular-nums' }, children: `${compactNumber(entry.calls)} calls` }),
          jsx('span', { style: { flexShrink: 0, color: COLORS.muted, fontSize: '11px', fontVariantNumeric: 'tabular-nums' }, children: `p95 ${formatMs(entry.p95_ms)} · med ${formatMs(entry.median_ms)}` }),
          denials > 0 ? jsx('span', { style: { flexShrink: 0, color: COLORS.bad, fontSize: '11px', fontVariantNumeric: 'tabular-nums' }, children: `${compactNumber(denials)} denied` }) : null,
          jsx(Badge, { variant: 'outline', style: { ...styles.metaBadge, color: pillColor, borderColor: pillColor, marginLeft: 'auto', flexShrink: 0 }, children: formatStatus(entry.verdict) })
        ]
      }, `verdict-${entry.tool || 'unknown'}`)
    }) })
  })
}

// Control-report status: surfaces GET /report-status freshness and hands the
// user a one-click path back to the report command. 'Open in chat' routes
// through the host bridge when present, otherwise falls back to copying the
// command with a short 'Copied' flash (same idiom as the RoutesCard fallback).
function ReportStatusCard({ api }) {
  const query = useQuery({ queryKey: ['sips', 'report-status'], queryFn: () => api.rest('/report-status'), refetchInterval: pollInterval(60000) })
  const [copied, setCopied] = useState(false)
  const title = 'Report status'
  const icon = 'window'

  const openInChat = () => {
    if (window.hermes && typeof window.hermes.send === 'function') {
      window.hermes.send('/sips-report')
      return
    }
    if (!navigator.clipboard?.writeText) return
    navigator.clipboard.writeText('/sips-report').then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }).catch(() => { /* clipboard unavailable — button still shows the command */ })
  }

  if (query.isLoading) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'Checking report status…' }) })
  }
  if (query.isError) {
    return jsx(Card, {
      title,
      icon,
      children: jsx('div', { style: styles.unavailable, children: 'The report-status endpoint is unavailable right now. Retry from the header refresh.' })
    })
  }

  const report = query.data || {}
  const ageHours = Number(report.age_hours)

  return jsx(Card, {
    title,
    icon,
    children: [
      report.available ? jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }, children: [
        jsx('span', { style: styles.label, children: 'Control report' }),
        jsxs('span', { style: { ...styles.value, fontVariantNumeric: 'tabular-nums' }, children: [
          formatRelativeTimestamp(report.generated_at),
          Number.isFinite(ageHours) ? jsx('span', { style: { color: COLORS.muted, fontWeight: 400 }, children: ` · ${ageHours.toFixed(1)}h old` }) : null
        ] })
      ] }) : jsx('div', { style: styles.unavailable, children: report.note || 'No report generated yet. Run /sips-report in chat.' }),
      jsx('div', { style: { display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }, children: jsx(Button, { variant: 'outline', size: 'sm', onClick: openInChat, children: copied ? 'Copied' : 'Open in chat' }) }),
      report.claim_boundary ? jsx('div', { style: { color: COLORS.muted, fontSize: '11px', marginTop: '10px' }, children: report.claim_boundary }) : null
    ]
  })
}

// Inline-widget strip: one chip per widget kind from GET /widgets — the kinds
// list comes from the backend probe, never hardcoded here. A chip runs
// '/sips-widget <kind>' in chat via the host bridge when present; without the
// bridge it copies the command with a short 'Copied' flash (same idiom as
// ReportStatusCard). Top-level available:false renders the note, no chips.
function WidgetStripCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'widgets'], queryFn: () => api.rest('/widgets'), refetchInterval: pollInterval(60000) })
  const [copiedKind, setCopiedKind] = useState(null)
  const title = 'Widget strip'
  const icon = 'layers'

  const runKind = (kind) => {
    const command = `/sips-widget ${kind}`
    if (window.hermes && typeof window.hermes.send === 'function') {
      window.hermes.send(command)
      return
    }
    if (!navigator.clipboard?.writeText) return
    navigator.clipboard.writeText(command).then(() => {
      setCopiedKind(kind)
      setTimeout(() => setCopiedKind((current) => (current === kind ? null : current)), 1500)
    }).catch(() => { /* clipboard unavailable — chip still shows the command */ })
  }

  if (query.isLoading) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'Probing widget kinds…' }) })
  }
  if (query.isError || !query.data?.available) {
    return jsx(Card, {
      title,
      icon,
      hint: 'Inline widgets render on demand in chat via /sips-widget.',
      children: jsx('div', { style: styles.unavailable, children: query.data?.note || 'The widgets endpoint is unavailable right now. Retry from the header refresh.' })
    })
  }

  const data = query.data
  const kinds = Array.isArray(data.kinds) ? data.kinds : []
  const briefFor = (kind) => (Array.isArray(data.widgets) ? data.widgets : []).find((brief) => brief.kind === kind)

  return jsx(Card, {
    title,
    icon,
    hint: `${compactNumber(kinds.length)} widget kind${kinds.length === 1 ? '' : 's'} · rendered on demand in chat`,
    children: [
      jsx('div', { style: styles.widgetChips, children: kinds.map((kind) => {
        const brief = briefFor(kind)
        const available = brief ? brief.available !== false : true
        const copied = copiedKind === kind
        return jsxs('button', {
          type: 'button',
          disabled: !available,
          onClick: () => runKind(kind),
          style: { ...styles.widgetChip, ...(!available ? styles.widgetChipDisabled : {}), ...(copied ? styles.widgetChipCopied : {}) },
          children: [
            jsx(Codicon, { name: 'window', size: '0.8rem' }),
            copied ? 'Copied' : `/sips-widget ${kind}`
          ]
        }, `widget-${kind}`)
      }) }),
      data.claim_boundary ? jsx('div', { style: { color: COLORS.muted, fontSize: '11px', marginTop: '10px' }, children: data.claim_boundary }) : null
    ]
  })
}

// At-a-glance strip: one useQuery to GET /overview-strip, four compact
// Signals (goal posture, fleet, worst tool, memory). Each leg degrades
// independently on the backend — a leg with available:false renders its note
// as muted text instead of fake zeros; the panel never invents 0 counts.
function OverviewStripCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'overview-strip'], queryFn: () => api.rest('/overview-strip'), refetchInterval: pollInterval(60000) })
  const title = 'At a glance'
  const icon = 'pulse'

  if (query.isLoading) {
    return jsx(Card, { title, icon, children: jsx('div', { style: styles.unavailable, children: 'Composing the glance strip…' }) })
  }
  if (query.isError) {
    return jsx(Card, {
      title,
      icon,
      hint: 'Composed from the same bounded lenses as the tab cards.',
      children: jsx('div', { style: styles.unavailable, children: 'The overview-strip endpoint is unavailable right now. Retry from the header refresh.' })
    })
  }

  const strip = query.data || {}
  const legs = []

  const goal = strip.goal
  if (goal?.available) {
    const subtasks = goal.subtasks || {}
    legs.push(jsx(Signal, {
      key: 'goal',
      label: 'Goal posture',
      value: formatStatus(goal.status),
      detail: `${Number(goal.progress_pct) || 0}% of subtasks done${subtasks.total ? ` (${compactNumber(subtasks.done)}/${compactNumber(subtasks.total)})` : ''}`,
      tone: toneFor(goal.status) === 'good' ? 'good' : 'warn',
      progress: Number(goal.progress_pct) || 0
    }))
  } else {
    legs.push(jsx('div', { key: 'goal', style: styles.unavailable, children: goal?.note || 'No active goal.' }))
  }

  const fleet = strip.fleet
  if (fleet?.available) {
    const statuses = Object.entries(fleet.statuses || {})
    legs.push(jsx(Signal, {
      key: 'fleet',
      label: 'Fleet',
      value: compactNumber(fleet.total),
      detail: statuses.length ? statuses.map(([status, count]) => `${count} ${status}`).join(' · ') : 'no campaigns',
      tone: 'accent'
    }))
  } else {
    legs.push(jsx('div', { key: 'fleet', style: styles.unavailable, children: fleet?.note || 'Fleet unavailable right now.' }))
  }

  const verdicts = strip.verdicts
  if (verdicts?.available) {
    legs.push(jsx(Signal, {
      key: 'verdicts',
      label: 'Worst tool',
      value: truncateMiddle(String(verdicts.worst_tool || 'unknown'), 14),
      detail: `${formatStatus(verdicts.worst_verdict)} · ${compactNumber(verdicts.calls_in_window)} calls in window`,
      tone: VERDICT_TONE[verdicts.worst_verdict] || 'muted'
    }))
  } else {
    legs.push(jsx('div', { key: 'verdicts', style: styles.unavailable, children: verdicts?.note || 'Verdicts unavailable right now.' }))
  }

  const memory = strip.memory
  if (memory?.available) {
    const recordCount = Number(memory.record_count) || 0
    const verified = Number(memory.verified_or_active_count) || 0
    legs.push(jsx(Signal, {
      key: 'memory',
      label: 'Memory',
      value: compactNumber(recordCount),
      detail: `${compactNumber(verified)} verified/active`,
      tone: 'good',
      progress: recordCount ? percent(verified, recordCount) : 0
    }))
  } else {
    legs.push(jsx('div', { key: 'memory', style: styles.unavailable, children: memory?.note || memory?.reason || 'Memory fabric unavailable right now.' }))
  }

  return jsx(Card, {
    title,
    icon,
    hint: strip.claim_boundary || 'Composed from the same bounded lenses as the tab cards; freshness per leg.',
    children: jsx('div', { style: styles.stripGrid, children: legs })
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

// Lifecycle lens: aggregates the agent hook stream (via GET /lifecycle) into
// tool-usage bars, an hourly activity histogram, session rollups, and any
// denials. Metadata only — the backend strips payloads and arguments.
function LifecycleCard({ api }) {
  const query = useQuery({ queryKey: ['sips-control-plane', 'lifecycle'], queryFn: () => api.rest('/lifecycle'), refetchInterval: pollInterval(30000) })

  if (query.isLoading) {
    return jsx(Card, { title: 'Lifecycle lens', icon: 'pulse', lead: true, children: jsx('div', { style: styles.unavailable, children: 'Reading the hook stream…' }) })
  }
  if (query.isError) {
    return jsx(Card, { title: 'Lifecycle lens', icon: 'pulse', lead: true, children: jsx('div', { style: styles.unavailable, children: 'The lifecycle endpoint is unavailable right now. Retry from the header refresh.' }) })
  }
  const lifecycle = query.data
  if (!lifecycle?.available) {
    return jsx(Card, {
      title: 'Lifecycle lens',
      icon: 'pulse',
      lead: true,
      hint: 'Backed by the agent hook stream.',
      children: jsx('div', { style: styles.unavailable, children: 'No hook stream is available yet — it fills as the SIPS lifecycle hooks observe tool calls and sessions.' })
    })
  }

  const tools = (lifecycle.tools || []).slice(0, 8)
  const maxTool = Math.max(...tools.map((row) => Number(row.total) || 0), 1)
  const histogram = lifecycle.histogram || []
  const maxHour = Math.max(...histogram.map((col) => Number(col.events) || 0), 1)
  const sessions = lifecycle.sessions || []
  const denials = lifecycle.denials || []

  return jsx(Card, {
    title: 'Lifecycle lens',
    icon: 'pulse',
    lead: true,
    hint: `${compactNumber(lifecycle.window_events || 0)} events in window · ${compactNumber(lifecycle.total_events || 0)} total`,
    children: [
      // Tool bars: one row per tool, segmented by outcome class.
      tools.length ? jsx('div', { style: { display: 'grid', gap: '7px' }, key: 'tools', children: tools.map((row) => {
        const total = Number(row.total) || 0
        const seg = (count) => `${(Number(count) || 0) / maxTool * 100}%`
        const issues = (Number(row.error) || 0) + (Number(row.denied) || 0)
        return jsxs('div', {
          children: [
            jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '3px' }, children: [
              jsx('span', { style: { fontSize: '12px', fontWeight: 650 }, children: row.tool }),
              jsxs('span', { style: { fontSize: '11px', color: issues ? COLORS.warn : COLORS.muted, fontVariantNumeric: 'tabular-nums' }, children: [
                compactNumber(total),
                issues ? ` · ${issues} issue${issues === 1 ? '' : 's'}` : ''
              ] })
            ] }),
            jsx('div', {
              style: { display: 'flex', height: '7px', borderRadius: '999px', overflow: 'hidden', background: 'rgba(255,255,255,0.06)' },
              role: 'img',
              'aria-label': `${row.tool}: ${total} events`,
              children: [
                jsx('div', { key: 'ok', style: { width: seg(row.ok), background: COLORS.good } }),
                jsx('div', { key: 'allowed', style: { width: seg(row.allowed), background: COLORS.accent, opacity: 0.7 } }),
                jsx('div', { key: 'issues', style: { width: seg(issues), background: COLORS.bad } }),
                jsx('div', { key: 'other', style: { width: seg(row.other), background: COLORS.muted, opacity: 0.5 } })
              ]
            })
          ]
        }, `tool-${row.tool}`)
      }) }) : jsx('div', { style: styles.unavailable, key: 'no-tools', children: 'No tool calls observed in the current window.' }),

      // Activity histogram: one column per hour, height scaled to the max.
      histogram.length ? jsxs('div', { key: 'histogram', children: [
        jsx('div', { style: { ...styles.label, margin: '14px 0 5px' }, children: 'Activity by hour (UTC)' }),
        jsx('div', { style: { display: 'flex', alignItems: 'flex-end', gap: '2px', height: '52px' }, children: histogram.map((col) => jsx('div', {
          title: `${col.hour} — ${col.events} events`,
          style: {
            flex: 1,
            minWidth: '3px',
            height: `${Math.max(6, (Number(col.events) || 0) / maxHour * 100)}%`,
            background: COLORS.accent,
            opacity: 0.55,
            borderRadius: '2px 2px 0 0'
          }
        }, col.hour)) }),
        jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', marginTop: '3px' }, children: [
          jsx('span', { style: { ...styles.label, fontSize: '10px' }, children: histogram[0]?.hour }),
          jsx('span', { style: { ...styles.label, fontSize: '10px' }, children: histogram[histogram.length - 1]?.hour })
        ] })
      ] }, 'histogram') : null,

      // Sessions: most recent first, id truncated.
      sessions.length ? jsxs('div', { key: 'sessions', children: [
        jsx('div', { style: { ...styles.label, margin: '14px 0 2px' }, children: 'Recent sessions' }),
        sessions.slice(0, 6).map((session) => jsxs('div', { style: styles.row, children: [
          jsx('span', { style: { fontSize: '12px', fontWeight: 600, fontFamily: 'var(--ui-mono, ui-monospace, monospace)', fontSizeAdjust: 'none' }, children: `${String(session.session_id || '').slice(0, 12)}…` }),
          jsxs('span', { style: { ...styles.value, color: COLORS.muted }, children: [
            `${compactNumber(session.events || 0)} events · ${session.tool_count || 0} tools`,
            session.last_ts ? ` · ${formatRelativeTimestamp(session.last_ts)}` : ''
          ] })
        ] }, session.session_id))
      ] }, 'sessions') : null,

      // Denials: warn block, only when present.
      denials.length ? jsx('div', {
        style: { marginTop: '12px', border: `1px solid ${COLORS.warn}`, borderRadius: '10px', padding: '10px 12px', background: 'rgba(244,199,107,0.08)' },
        key: 'denials',
        children: [
          jsx('div', { style: { fontSize: '12px', fontWeight: 700, color: COLORS.warn, marginBottom: '5px' }, children: `${denials.length} denied/blocked event${denials.length === 1 ? '' : 's'}` }),
          ...denials.slice(0, 10).map((denial, index) => jsxs('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: COLORS.muted, padding: '2px 0' }, children: [
            jsx('span', { children: denial.tool || 'unknown tool' }),
            jsx('span', { children: formatRelativeTimestamp(denial.ts) })
          ] }, `denial-${index}`))
        ]
      }) : null,

      jsx('div', { style: { ...styles.label, fontSize: '11px', marginTop: '12px', lineHeight: 1.5 }, key: 'boundary', children: lifecycle.claim_boundary })
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

function SurfaceCard({ counts, lifecycle, onOpenActivity }) {
  const rows = [['Commands', counts?.commands], ['Agents', counts?.agents], ['Scripts', counts?.scripts], ['Hook event types', counts?.hook_events], ['MCP servers', counts?.mcp_servers], ['MCP tools', counts?.mcp_tools]]
  const max = Math.max(...rows.map(([, value]) => Number(value) || 0), 1)
  const topTool = lifecycle?.available ? (lifecycle.tools || [])[0] : null

  return jsx(Card, {
    title: 'SIPS surface inventory',
    icon: 'layers',
    hint: 'Declared capability footprint across the local control plane.',
    children: [
      jsx('div', {
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
                children: [jsx('span', { style: styles.label, children: label }), jsx(FlipValue, { value: compactNumber(amount), weight: 750 })]
              }),
              jsx('div', { style: styles.miniTrack, children: jsx('div', { style: { ...styles.miniFill, width: `${width}%`, background: COLORS.accent } }) })
            ]
          })
        })
      }),
      topTool ? jsxs('button', {
        type: 'button',
        onClick: onOpenActivity,
        style: { marginTop: '10px', width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', padding: '7px 10px', border: `1px solid ${COLORS.border}`, borderRadius: '9px', background: 'transparent', cursor: 'pointer', color: 'inherit', font: 'inherit' },
        children: [
          jsxs('span', { style: { ...styles.label, textAlign: 'left' }, children: ['Busiest tool (window): ', jsx('span', { style: { fontWeight: 650, color: COLORS.text }, children: topTool.tool })] }),
          jsxs('span', { style: { ...styles.value, color: COLORS.accent }, children: ['×', compactNumber(topTool.total), ' · view lens'] })
        ]
      }, 'lifecycle-chip') : null
    ]
  })
}

function SipsPulse({ api }) {
  const gateway = useValue(host.state.gateway)
  const query = useQuery({ queryKey: ['sips-control-plane', 'status'], queryFn: () => api.rest(API_STATUS), refetchInterval: pollInterval(15000) })
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
  const query = useQuery({ queryKey: ['sips-control-plane', 'status'], queryFn: () => api.rest(API_STATUS), refetchInterval: pollInterval(15000) })
  const data = query.data
  const counts = data?.surface_counts || {}
  const actionState = useSipsActions(api, data, query.isError)
  const selfloopQuery = useQuery({ queryKey: ['sips-control-plane', 'selfloop'], queryFn: () => api.rest('/selfloop'), refetchInterval: pollInterval(30000) })
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
    jsxs('header', { style: styles.header, children: [jsx('div', { children: [jsx('div', { style: styles.eyebrow, children: 'SIPS CONTROL PLANE — OPERATIONS BOARD' }), jsx('h1', { style: styles.title, children: 'The Board' }), jsx('p', { style: styles.subtitle, children: data.claim_boundary || 'Read-only operational view of SIPS health, proof, goals, memory, and lifecycle activity. Every value flips when it changes; amber is attention, red is failure, nothing is decoration.' })] }), jsx('div', { style: styles.actions, children: [jsx(Button, { variant: 'outline', size: 'sm', onClick: () => query.refetch(), children: refreshLabel })] })] }),
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
          jsx('span', { style: styles.tabBarLabel, children: 'Platforms' })
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
            tab.count ? jsx('span', { style: { ...styles.tabCount, marginLeft: '3px' }, children: tab.count }) : null
          ]
        }, `tab-${tab.id}`)) })
      ] }),
      jsxs('div', { style: styles.workspace, 'data-sips-workspace': true, key: activeTab, children: [
      // Lead/support structure per workspace: the reason-for-visit leads;
      // supporting cards subordinate below. Squint test: one lead per tab.
      activeTab === 'overview' ? jsxs('div', { children: [
        jsx('div', { style: styles.leadRow, children: jsx(GoalBoardCard, { api }) }),
        jsx('div', { style: styles.leadRow, children: jsx(OverviewStripCard, { api }) }),
        jsx('div', { style: styles.supportGrid, children: [
          jsx(GoalCard, { goal: data.goal, api, selfloop: selfloopQuery.data, onSelfloopMutated: () => selfloopQuery.refetch() }),
          jsx(RuntimeCard, { api }),
          jsx(RunsCard, { api }),
          jsx(FleetCard, { api }),
          jsx(TimelineCard, { api }),
          jsx(MemoryBrowser, { api }),
          jsx(MemoryCard, { memory: data.memory }),
          jsx(SurfaceCard, { counts, lifecycle: data.lifecycle, onOpenActivity: () => switchTab('activity') }),
          jsx(WidgetStripCard, { api }),
          jsx(ContextScanCard, { api })
        ] })
      ] }) : null,
      activeTab === 'verification' ? jsxs('div', { children: [
        jsx('div', { style: styles.leadRow, children: jsx(ActionCenter, { actionState }) }),
        jsx('div', { style: styles.supportGrid, children: [
          jsx(HistoryCard, { api }),
          jsx(ProofCard, { proof: data.proof_layers, actionState }),
          jsx(RoutesCard, { api }),
          jsx(ReportStatusCard, { api }),
          jsx(GateMatrixCard, { api })
        ] })
      ] }) : null,
      activeTab === 'memory' ? jsxs('div', { style: styles.supportGrid, children: [
        jsx(RecallCard, { api }),
        jsx(RecordCard, { api })
      ] }) : null,
      activeTab === 'activity' ? jsxs('div', { children: [
        jsx('div', { style: styles.leadRow, children: jsx(LifecycleCard, { api }) }),
        jsx('div', { style: styles.supportGrid, children: [
          jsx(ToolCallsCard, { api }),
          jsx(TokenUsageCard, { api }),
          jsx(ToolLatencyCard, { api }),
          jsx(VerdictsCard, { api }),
          jsx(HookFlowCard, { events: data.events }),
          jsx(EventsCard, { events: data.events })
        ] })
      ] }) : null
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
        // --- THE BOARD: cascade + lamps + flip --------------------------------
        `@keyframes sips-flip-in { 0% { transform: rotateX(88deg); opacity: 0.2; } 60% { transform: rotateX(-14deg); opacity: 1; } 100% { transform: rotateX(0deg); opacity: 1; } }`,
        `.sips-flip-in { animation: sips-flip-in 300ms cubic-bezier(0.2, 0.7, 0.3, 1) both; transform-origin: 50% 50%; backface-visibility: hidden; }`,
        `[data-sips-page] button:focus-visible, [data-sips-page] select:focus-visible, [data-sips-page] summary:focus-visible, [data-sips-page] a:focus-visible { outline: 2px solid ${COLORS.amber}; outline-offset: 2px; border-radius: 4px; }`,
        `@property --sips-orb { syntax: '<percentage>'; inherits: false; initial-value: 0%; }`,
        // Board panels: resting cards sit in the chassis; leads project.
        `[data-sips-card] { transition: transform 160ms cubic-bezier(0.2,0.7,0.3,1), box-shadow 160ms cubic-bezier(0.2,0.7,0.3,1), border-color 160ms ease; }`,
        `[data-sips-card]:hover { transform: translateY(-2px); border-top-color: #454a52; box-shadow: 0 2px 4px rgba(0,0,0,0.5), 0 14px 32px rgba(0,0,0,0.42); }`,
        `[data-sips-lead]:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.55), 0 24px 52px rgba(0,0,0,0.48); }`,
        `[data-sips-lead] { transition: transform 180ms cubic-bezier(0.2,0.7,0.3,1), box-shadow 180ms cubic-bezier(0.2,0.7,0.3,1); }`,
        `input, select, textarea { box-shadow: inset 0 1px 3px rgba(0,0,0,0.5); }`,
        // Orbit lamp: selfloop indicator circling the hero frame while active.
        `[data-sips-selfloop] { position: relative; overflow: hidden; }`,
        `[data-sips-selfloop="on"]::after { content: ''; position: absolute; inset: 0; border-radius: inherit; pointer-events: none; border: 1px solid rgba(255,176,0,0.0); box-shadow: inset 0 0 0 0 rgba(255,176,0,0); animation: sips-lamp-pulse 3.2s ease-in-out infinite; }`,
        `@keyframes sips-lamp-pulse { 0%, 100% { box-shadow: inset 0 0 0 0 rgba(255,176,0,0); border-color: rgba(255,176,0,0); } 50% { box-shadow: inset 0 0 18px -6px rgba(255,176,0,0.28); border-color: rgba(255,176,0,0.35); } }`,
        // Platform rail states: flap tile tabs; active tab lights.
        `[data-sips-railitem] { transition: background 130ms ease, color 130ms ease, border-color 130ms ease; }`,
        `[data-sips-railitem]:hover { background: ${COLORS.flap}; border-color: ${COLORS.seam}; color: ${COLORS.letter}; }`,
        `[data-sips-railitem="active"] { background: ${COLORS.flapRaised}; border-color: rgba(255,176,0,0.30); color: ${COLORS.letter}; box-shadow: inset 2px 0 0 ${COLORS.amber}; }`,
        // Push button press.
        `[data-sips-push] { transition: transform 90ms ease, box-shadow 90ms ease; }`,
        `[data-sips-push]:not(:disabled):active { transform: translateY(1px); box-shadow: inset 0 4px 9px rgba(0,0,0,0.85), inset 0 1px 2px rgba(0,0,0,0.65); }`,
        `[data-sips-push]:not(:disabled):active span { transform: translateY(1px); }`,
        `[data-sips-push] span { transition: transform 90ms ease; }`,
        // Workspace mount + heartbeat dot.
        `[data-sips-workspace] { animation: sips-mount 170ms cubic-bezier(0.2,0.7,0.3,1) both; }`,
        `@keyframes sips-mount { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }`,
        `[data-sips-heartbeat] { animation: sips-lamp-pulse 2.6s ease-in-out infinite; animation-play-state: paused; border-radius: 999px; }`,
        `[data-sips-heartbeat="on"] { animation-play-state: running; }`,
        // Progress fills: amber sweep with a lamp glint at the leading edge.
        `.sips-progress-fill { position: relative; overflow: hidden; }`,
        `.sips-progress-fill::after { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(45deg, rgba(0,0,0,0.14) 0 4px, transparent 4px 9px); }`,
        // Reduced motion: the board becomes a static timetable.
        `@media (prefers-reduced-motion: reduce) { .sips-flip-in { animation: none !important; } [data-sips-heartbeat] { animation: none !important; } [data-sips-card], [data-sips-lead] { transition: none !important; } [data-sips-card]:hover, [data-sips-lead]:hover { transform: none !important; } [data-sips-selfloop="on"]::after, [data-sips-workspace] { animation: none !important; } [data-sips-railitem], [data-sips-push], [data-sips-push] span { transition: none !important; } .sips-dial-needle, .sips-toggle-knob { transition: none !important; } }`
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
