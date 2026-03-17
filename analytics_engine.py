"""
Analytics Engine for RecruitAI
================================
Computes all dashboard metrics from existing screening results.
No new ML needed — aggregates data already saved.
"""

import os
import json
from datetime import datetime
from collections import defaultdict, Counter
from config import Config


class AnalyticsEngine:

    def __init__(self):
        self.results_folder = Config.RESULTS_FOLDER
        self.jd_folder      = Config.JD_STORE_FOLDER

    # ── MAIN METHOD — returns everything dashboard needs ──────────────────────
    def get_dashboard_data(self):
        """Compute all analytics and return as a single dict."""
        screenings = self._load_all_screenings()

        if not screenings:
            return self._empty_dashboard()

        return {
            'overview'        : self._compute_overview(screenings),
            'monthly_trends'  : self._compute_monthly_trends(screenings),
            'top_positions'   : self._compute_top_positions(screenings),
            'avg_scores'      : self._compute_avg_scores(screenings),
            'shortlist_rates' : self._compute_shortlist_rates(screenings),
            'missing_skills'  : self._compute_missing_skills(screenings),
            'recent'          : self._compute_recent(screenings),
            'total_screenings': len(screenings),
        }

    # ── LOAD ALL SCREENINGS ───────────────────────────────────────────────────
    def _load_all_screenings(self):
        screenings = []
        if not os.path.exists(self.results_folder):
            return screenings
        for file in os.listdir(self.results_folder):
            if not file.endswith('.json'):
                continue
            try:
                with open(os.path.join(self.results_folder, file)) as f:
                    data = json.load(f)
                if data.get('candidates'):
                    screenings.append(data)
            except:
                pass
        return screenings

    # ── OVERVIEW CARDS ────────────────────────────────────────────────────────
    def _compute_overview(self, screenings):
        total      = 0
        shortlisted = 0
        on_hold    = 0
        rejected   = 0
        scores     = []

        for s in screenings:
            for c in s.get('candidates', []):
                total += 1
                score  = c.get('overall_score', 0)
                scores.append(score)
                action = c.get('decision', {}).get('action', '')
                if action == 'shortlist':
                    shortlisted += 1
                elif action == 'consider':
                    on_hold += 1
                else:
                    rejected += 1

        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        shortlist_rate = round((shortlisted / total * 100), 1) if total else 0

        return {
            'total_candidates' : total,
            'shortlisted'      : shortlisted,
            'on_hold'          : on_hold,
            'rejected'         : rejected,
            'avg_score'        : avg_score,
            'shortlist_rate'   : shortlist_rate,
            'total_screenings' : len(screenings),
        }

    # ── MONTHLY TRENDS ────────────────────────────────────────────────────────
    def _compute_monthly_trends(self, screenings):
        monthly = defaultdict(lambda: {'screened': 0, 'shortlisted': 0})

        for s in screenings:
            # Get date from screening metadata
            created = s.get('created_at') or s.get('timestamp') or s.get('job', {}).get('created_at', '')
            if not created:
                continue
            try:
                dt    = datetime.fromisoformat(created[:19])
                month = dt.strftime('%b %Y')   # e.g. "Jan 2026"
                key   = dt.strftime('%Y-%m')   # for sorting
            except:
                continue

            for c in s.get('candidates', []):
                monthly[key]['screened'] += 1
                monthly[key]['month']     = month
                if c.get('decision', {}).get('action') == 'shortlist':
                    monthly[key]['shortlisted'] += 1

        # Sort by key (YYYY-MM) and return last 6 months
        sorted_months = sorted(monthly.items())[-6:]
        result = []
        max_val = 1

        for key, data in sorted_months:
            result.append({
                'month'      : data.get('month', key),
                'screened'   : data['screened'],
                'shortlisted': data['shortlisted'],
            })
            max_val = max(max_val, data['screened'])

        # Add percentage width for CSS bars
        for r in result:
            r['screened_pct']    = round(r['screened'] / max_val * 100)
            r['shortlisted_pct'] = round(r['shortlisted'] / max_val * 100)

        return result

    # ── TOP JOB POSITIONS ─────────────────────────────────────────────────────
    def _compute_top_positions(self, screenings):
        position_counts = Counter()

        for s in screenings:
            title = s.get('job', {}).get('title', 'Unknown')
            # Clean title
            title = title.replace('_', ' ').title()
            position_counts[title] += len(s.get('candidates', []))

        top = position_counts.most_common(6)
        if not top:
            return []

        max_val = top[0][1] if top else 1
        return [
            {
                'title'  : title,
                'count'  : count,
                'pct'    : round(count / max_val * 100)
            }
            for title, count in top
        ]

    # ── AVERAGE SCORES PER JOB ────────────────────────────────────────────────
    def _compute_avg_scores(self, screenings):
        job_scores = defaultdict(list)

        for s in screenings:
            title = s.get('job', {}).get('title', 'Unknown').replace('_', ' ').title()
            for c in s.get('candidates', []):
                score = c.get('overall_score', 0)
                if score > 0:
                    job_scores[title].append(score)

        result = []
        for title, scores in job_scores.items():
            avg = round(sum(scores) / len(scores), 1)
            result.append({
                'title': title,
                'avg'  : avg,
                'pct'  : round(avg)   # score is already 0-100
            })

        # Sort by avg descending, take top 6
        result.sort(key=lambda x: x['avg'], reverse=True)
        return result[:6]

    # ── SHORTLIST RATE PER JOB ────────────────────────────────────────────────
    def _compute_shortlist_rates(self, screenings):
        job_data = defaultdict(lambda: {'total': 0, 'shortlisted': 0})

        for s in screenings:
            title = s.get('job', {}).get('title', 'Unknown').replace('_', ' ').title()
            for c in s.get('candidates', []):
                job_data[title]['total'] += 1
                if c.get('decision', {}).get('action') == 'shortlist':
                    job_data[title]['shortlisted'] += 1

        result = []
        for title, data in job_data.items():
            rate = round(data['shortlisted'] / data['total'] * 100, 1) if data['total'] else 0
            result.append({
                'title'      : title,
                'rate'       : rate,
                'shortlisted': data['shortlisted'],
                'total'      : data['total'],
                'pct'        : round(rate),
            })

        result.sort(key=lambda x: x['rate'], reverse=True)
        return result[:6]

    # ── MISSING SKILLS ────────────────────────────────────────────────────────
    def _compute_missing_skills(self, screenings):
        skill_counter = Counter()

        for s in screenings:
            for c in s.get('candidates', []):
                for skill in c.get('missing_skills', []):
                    # handle both plain strings and dicts like {'skill': 'Docker'}
                    if isinstance(skill, dict):
                        skill = skill.get('skill') or skill.get('name') or str(skill)
                    skill_counter[str(skill).lower().strip()] += 1

        top_skills = skill_counter.most_common(10)
        if not top_skills:
            return []

        max_count = top_skills[0][1] if top_skills else 1
        return [
            {
                'skill': skill.title(),
                'count': count,
                'pct'  : round(count / max_count * 100)
            }
            for skill, count in top_skills
        ]

    # ── RECENT SCREENINGS TABLE ───────────────────────────────────────────────
    def _compute_recent(self, screenings):
        result = []

        for s in screenings:
            candidates  = s.get('candidates', [])
            shortlisted = len([c for c in candidates if c.get('decision', {}).get('action') == 'shortlist'])
            scores      = [c.get('overall_score', 0) for c in candidates if c.get('overall_score', 0) > 0]
            avg_score   = round(sum(scores) / len(scores), 1) if scores else 0

            created = s.get('created_at') or s.get('timestamp') or s.get('job', {}).get('created_at', '')
            try:
                date = datetime.fromisoformat(created[:19]).strftime('%d %b %Y')
            except:
                date = 'Unknown'

            result.append({
                'screening_id': s.get('screening_id', ''),
                'title'       : s.get('job', {}).get('title', 'Unknown').replace('_', ' ').title(),
                'date'        : date,
                'total'       : len(candidates),
                'shortlisted' : shortlisted,
                'avg_score'   : avg_score,
                'rate'        : round(shortlisted / len(candidates) * 100, 1) if candidates else 0,
            })

        # Sort by date newest first
        result.sort(key=lambda x: x['date'], reverse=True)
        return result[:10]

    # ── EMPTY STATE ───────────────────────────────────────────────────────────
    def _empty_dashboard(self):
        return {
            'overview'        : {'total_candidates': 0, 'shortlisted': 0, 'on_hold': 0,
                                 'rejected': 0, 'avg_score': 0, 'shortlist_rate': 0, 'total_screenings': 0},
            'monthly_trends'  : [],
            'top_positions'   : [],
            'avg_scores'      : [],
            'shortlist_rates' : [],
            'missing_skills'  : [],
            'recent'          : [],
            'total_screenings': 0,
        }


# Singleton
analytics_engine = AnalyticsEngine()