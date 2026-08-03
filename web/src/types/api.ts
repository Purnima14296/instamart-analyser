export type RoleName = 'viewer' | 'reviewer' | 'admin'

export type JobKind =
  | 'enrich'
  | 'phase3'
  | 'phase4'
  | 'phase5'
  | 'ingest_play'
  | 'ingest_appstore'
  | 'ingest_reddit_selenium'
  | 'ingest_all'
  | 'analysis_cascade'

export interface ResearchSummary {
  product: string
  title: string
  subtitle: string
  executive_brief: string
  key_findings: string[]
  portfolio: {
    reviews_ingested: number
    source_counts: Record<string, number>
    play_store: number
    app_store: number
    reddit: number
    themes_discovered: number
    insights_count: number
    opportunities_count: number
    avg_rating: number | null
    analysis_sample: number
    analysis_pending: number
    cohort_size: number
    coverage_pct: number
  }
  sentiment: {
    source: string
    counts: Record<string, number>
    percentages: Record<string, number>
    total: number
  }
  discovery_trust: {
    score: number
    label: string
    components: Record<string, number>
    formula: string
  }
  segment_priority: {
    recommended_focus: SegmentPriorityRow | null
    segments: SegmentPriorityRow[]
    formula: string
  }
  top_opportunity: {
    opportunity_id?: string
    title?: string
    opportunity_statement?: string
    user_problem?: string
    affected_segment?: string
    supporting_record_count?: number
    priority_score?: number
    priority_band?: string
    opportunity_types?: string[]
    recommended_moves?: string[]
  } | null
  top_challenge: {
    name: string
    count: number
    detail: string
  }
  research_grounding: Record<string, number>
  pipeline_status: {
    active_job: Job | null
    last_job: Job | null
    enrichment_pending?: number
    quota_blocked?: boolean
    quota_message?: string
  }
  pilot: {
    pilot_ready?: boolean
    alignment_verdict?: string
    open_defects?: number
  }
  bias_notes: string[]
  score_formulas: Record<string, string>
}

export interface NamedCount {
  name: string
  count: number
}

export interface ThemeCluster {
  theme_id: string
  primary_barrier: string
  shopping_mission: string
  primary_category: string
  analysis_bucket: string
  total_supporting_records: number
  source_breakdown: Record<string, number>
  affected_segment: string
  segment_breakdown: Record<string, number>
  cooccurring_barriers: Record<string, number>
  category_exploration_barrier?: string[]
  discovery_trigger?: string[]
  required_trust_signal?: string[]
  experimentation_likelihood?: string
  supporting_evidence?: EvidenceItem[]
}

export interface ThemesResponse {
  created_at?: string
  enriched_record_count?: number
  cluster_count?: number
  top_barriers: [string, number][]
  top_missions: [string, number][]
  top_segments: [string, number][]
  top_discovery_barriers: [string, number][]
  bias_notes: string[]
  clusters: ThemeCluster[]
}

export interface SourceAnalysis {
  total_reviews: number
  source_count: number
  sources: Array<{
    source: string
    count: number
    share_pct: number
    avg_rating: number | null
    rated_count: number
    enriched_count: number
    enriched_pct: number
    sentiment_pct: Record<string, number>
    top_barriers: NamedCount[]
  }>
  rating_distribution: Record<string, number>
  coverage_note: string
  bias_notes: string[]
}

export interface ReviewRow {
  record_id: string
  source: string
  rating?: number | null
  title?: string | null
  url?: string | null
  timestamp?: string | null
  body_text: string
  enriched: boolean
  sentiment?: string | null
  shopping_mission?: string | null
  user_segment?: string | null
  barriers: string[]
  categories_mentioned: string[]
  habit_signal?: boolean | null
  experimentation_signal?: boolean | null
}

export interface ReviewSearchResponse {
  total_matched: number
  returned: number
  offset: number
  limit: number
  facets: {
    sources: string[]
    segments: string[]
    missions: string[]
    barriers: string[]
    sentiments: string[]
  }
  reviews: ReviewRow[]
}

export interface DiscoveryChallenges {
  created_at?: string
  challenge_count: number
  challenges: Array<{
    theme: string
    category_exploration_barrier?: string[]
    supporting_review_count: number
    affected_segment: string
    confidence: string
    evidence_examples?: EvidenceItem[]
    evidence_count?: number
    product_opportunity?: string
  }>
  barrier_totals: NamedCount[]
  discovery_channels: NamedCount[]
  top_discovery_barriers: [string, number][]
  bias_notes: string[]
}

export interface SegmentExplorer {
  created_at?: string
  segment_count: number
  segments: Array<{
    segment: string
    review_count: number
    top_missions?: [string, number][]
    top_barriers?: [string, number][]
    top_discovery_barriers?: [string, number][]
    experimentation_likelihood?: [string, number][]
    priority?: SegmentPriorityRow | null
  }>
  recommended_focus: SegmentPriorityRow | null
  formula: string
  bias_notes: string[]
}

export interface RootCauseAnalysis {
  analyzed_records: number
  cause_group_count: number
  causes: Array<{
    barrier: string
    affected_reviews: number
    root_causes: NamedCount[]
    top_segments: NamedCount[]
    top_missions: NamedCount[]
    sentiment: Record<string, number>
    evidence: EvidenceItem[]
    confidence: string
  }>
  method: string
  bias_notes: string[]
}

export interface UnmetNeeds {
  analyzed_records: number
  need_count: number
  needs: Array<{
    need: string
    mentions: number
    top_segments: NamedCount[]
    evidence: EvidenceItem[]
    confidence: string
  }>
  category_opportunities: Array<Record<string, unknown>>
  linked_opportunities: Array<{
    opportunity_id?: string
    title?: string
    priority_band?: string
  }>
  bias_notes: string[]
}

export interface DiscoveryJourney {
  analyzed_records: number
  stages: Array<{
    stage: string
    description: string
    items: NamedCount[]
  }>
  behaviour_signals: {
    habit_pct: number
    experimentation_pct: number
    urgency_pct: number
    convenience_pct: number
    habit_count: number
    experimentation_count: number
  }
  shopping_behaviour: Array<Record<string, unknown>>
  bias_notes: string[]
}

export interface ValidationReport {
  method?: string
  alignment_verdict?: string
  aligned_top5_count?: number
  comparisons: Array<{
    barrier: string
    pre_llm_mapped_count: number
    ai_enriched_count: number
    pre_llm_rank: number | null
    ai_rank: number | null
    aligned_in_top5: boolean
  }>
  pilot_ready?: boolean
  open_defects?: number
  feedback_responses?: number
  refinements: {
    prompt: Array<Record<string, unknown>>
    taxonomy: Array<Record<string, unknown>>
    threshold: Array<Record<string, unknown>>
  }
  pilot_scope: Record<string, unknown>
  stakeholder_feedback_count: number
  bias_notes: string[]
}

export interface SegmentPriorityRow {
  rank: number
  segment: string
  review_count: number
  pct_sample: number
  discovery_barrier_rate: number
  trust_barrier_rate: number
  priority_score: number
  top_frustration?: string | null
  recommended?: boolean
  top_missions?: [string, number][]
  top_discovery_barriers?: [string, number][]
}

export interface OverviewResponse {
  enrichment: {
    cohort_size: number
    enriched_count: number
    error_count: number
    coverage_pct: number
    remaining_to_enrich?: number
    usage_today: {
      date: string
      requests: number
      tokens: number
      enrichment_calls: number
      limits: {
        enrichment_daily_cap: number
        daily_token_budget: number
      }
      remaining_enrichment_estimate: number
      remaining_token_estimate?: number
    }
    quota_blocked?: boolean
    quota_message?: string
    groq_key_configured: boolean
    can_start_enrichment?: boolean
  }
  theme_summary: {
    created_at?: string
    cluster_count?: number
    enriched_record_count?: number
    top_barriers: [string, number][]
    top_missions: [string, number][]
    top_segments: [string, number][]
    bias_notes: string[]
  }
  insights: {
    insight_count: number
    dry_run?: boolean
    created_at?: string
  }
  opportunities: {
    opportunity_count: number
    hypothesis_count: number
    priority_band_breakdown: Record<string, number>
  }
  pilot: {
    pilot_ready?: boolean
    alignment_verdict?: string
    open_defects?: number
    metric_count?: number
  }
  sample_size: number
  bias_notes: string[]
  known_limitations?: string[]
  operational_notes?: string[]
}

export interface EvidenceItem {
  record_id: string
  source?: string
  snippet: string
}

export interface Insight {
  insight_id: string
  status: string
  statement: string
  confidence: string
  affected_segment: string
  business_implication: string
  total_supporting_records: number
  supporting_evidence: EvidenceItem[]
  open_questions?: string[]
  primary_barriers?: string[]
  theme_ids?: string[]
  source_breakdown?: Record<string, number>
  review?: {
    status: string
    notes?: string
    reviewed_by?: string
    updated_at?: string
  } | null
  bias_notes?: string[]
}

export interface InsightsResponse {
  created_at?: string
  dry_run?: boolean
  count: number
  bias_notes: string[]
  insights: Insight[]
}

export interface Opportunity {
  opportunity_id: string
  rank?: number
  title: string
  opportunity_types: string[]
  intervention_area: string
  user_problem: string
  opportunity_statement: string
  recommended_moves: string[]
  expected_business_effect: string
  affected_segment: string
  shopping_mission: string
  confidence: string
  supporting_record_count: number
  priority: {
    score: number
    priority_band: string
  }
  evidence_examples?: EvidenceItem[]
  assumptions_and_unknowns?: string[]
}

export interface Hypothesis {
  hypothesis_id: string
  priority_rank: number
  hypothesis: string
  proposed_intervention: string
  primary_metric: string
  guardrail_metrics: string[]
  confidence: string
  expected_effect?: string
}

export interface MeasurementFramework {
  north_star: string
  metric_count: number
  guardrail_count: number
  core_metrics: Array<{
    metric_id: string
    name: string
    definition: string
    owner: string
  }>
  guardrail_metrics: Array<{
    metric_id: string
    name: string
    definition: string
  }>
  measurement_notes?: string[]
}

export interface Job {
  job_id: string
  job_type: string
  status: string
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  message?: string
  error?: string | null
  progress?: Record<string, unknown>
  failure_class?: string | null
  recovery_hint?: string
}

export interface FeedbackPayload {
  reviewer: string
  role: 'product' | 'research' | 'growth' | 'other'
  overall_usefulness: 'high' | 'medium' | 'low'
  trust_in_outputs: 'high' | 'medium' | 'low'
  would_use_for_experiment_planning: boolean
  comments: string[]
  defects: Array<{
    issue: string
    severity: 'high' | 'medium' | 'low'
    status: 'open' | 'incorporated' | 'deferred'
  }>
}
