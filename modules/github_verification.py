import requests
import os
import json
import time
from datetime import datetime, timedelta
from collections import Counter
from dateutil import parser  # Add this line
import pytz  # Add this line

class GitHubVerifier:
    """
    GitHub verification module that validates candidate skills
    using GitHub API (no scraping, rate-limit aware)
    """
    
    def __init__(self, config):
        self.config = config
        self.github_token = os.environ.get('GITHUB_TOKEN', None)
        self.cache_folder = os.path.join(config.BASE_DIR, 'github_cache')
        os.makedirs(self.cache_folder, exist_ok=True)
        
        # Rate limiting
        self.remaining_requests = 60
        self.reset_time = datetime.now()
        
        # GitHub API base URL
        self.api_base = "https://api.github.com"
        
        # Headers for authentication (if token available)
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'RecruitAI-Screening'
        }
        if self.github_token:
            self.headers['Authorization'] = f'token {self.github_token}'


    def verify_github(self, username, claimed_skills=None):
        """
        Main verification function - fetches GitHub data and computes score
        """
        print(f"\n🔍 Starting GitHub verification for: {username}")
        print(f"📡 Making API calls to GitHub...")
        
        if not username or username.strip() == '':
            print("❌ No username provided")
            return self._empty_result("No GitHub username provided")
        
        try:
            # Check cache first
            cached = self._check_cache(username)
            if cached:
                print(f"✅ Using cached data for {username}")
                print(f"   Cached score: {cached.get('github_score')}")
                return cached
            
            print(f"📡 Fetching user data from GitHub API...")
            # Fetch user data
            user_data = self._fetch_user(username)
            if not user_data:
                print(f"❌ User not found: {username}")
                return self._empty_result("User not found")
            
            print(f"✅ User found: {user_data.get('login')}")
            print(f"   Name: {user_data.get('name')}")
            print(f"   Public repos: {user_data.get('public_repos')}")
            print(f"   Followers: {user_data.get('followers')}")
            print(f"   Account created: {user_data.get('created_at')}")
            
            # Fetch repos
            print(f"📡 Fetching repositories...")
            repos = self._fetch_repos(username)
            print(f"✅ Found {len(repos)} repositories")
            
            # Calculate scores
            print(f"📊 Calculating GitHub score...")
            breakdown = self._calculate_breakdown(user_data, repos)
            total_score = self._calculate_total_score(breakdown)
            
            print(f"✅ GitHub Score: {total_score}")
            print(f"   Breakdown: {breakdown}")
            
            # Extract languages
            languages = self._extract_languages(repos)
            print(f"   Languages: {list(languages.keys())}")
            
            # ... rest of the method ...
            
        except Exception as e:
            print(f"❌ GitHub verification error: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_result(f"Error: {str(e)}")
    
    # def verify_github(self, username, claimed_skills=None):
    #     """
    #     Main verification function - fetches GitHub data and computes score
        
    #     Args:
    #         username: GitHub username
    #         claimed_skills: List of skills claimed in resume
        
    #     Returns:
    #         dict: Complete GitHub verification result
    #     """
    #     if not username or username.strip() == '':
    #         return self._empty_result("No GitHub username provided")
        
    #     try:
    #         # Check cache first
    #         cached = self._check_cache(username)
    #         if cached:
    #             return cached
            
    #         # Fetch user data
    #         user_data = self._fetch_user(username)
    #         if not user_data:
    #             return self._empty_result("User not found")
            
    #         # Fetch repos
    #         repos = self._fetch_repos(username)
            
    #         # Calculate scores
    #         breakdown = self._calculate_breakdown(user_data, repos)
    #         total_score = self._calculate_total_score(breakdown)
            
    #         # Extract languages
    #         languages = self._extract_languages(repos)
            
    #         # Check account age for fraud detection
    #         account_age = self._get_account_age(user_data)
    #         is_new_account = account_age.days < 30
            
    #         result = {
    #             'username': username,
    #             'github_score': total_score,
    #             'breakdown': breakdown,
    #             'languages_used': languages,
    #             'repo_count': len(repos),
    #             'account_age_days': account_age.days,
    #             'is_new_account': is_new_account,
    #             'account_created': user_data.get('created_at', ''),
    #             'follower_count': user_data.get('followers', 0),
    #             'following_count': user_data.get('following', 0),
    #             'public_repos': user_data.get('public_repos', 0),
    #             'has_blog': bool(user_data.get('blog')),
    #             'has_company': bool(user_data.get('company')),
    #             'has_bio': bool(user_data.get('bio')),
    #             'timestamp': datetime.now().isoformat()
    #         }
            
    #         # Cross-verify with claimed skills if provided
    #         if claimed_skills:
    #             result['skill_verification'] = self._cross_verify_skills(
    #                 claimed_skills, languages, repos
    #             )
            
    #         # Cache the result
    #         self._save_cache(username, result)
            
    #         return result
            
    #     except Exception as e:
    #         print(f"GitHub verification error for {username}: {e}")
    #         return self._empty_result(f"Error: {str(e)}")
    
    def _fetch_user(self, username):
        """Fetch user data from GitHub API"""
        url = f"{self.api_base}/users/{username}"
        
        response = self._make_request(url)
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def _fetch_repos(self, username):
        """Fetch repositories (sorted by stars)"""
        repos = []
        page = 1
        
        while True:
            url = f"{self.api_base}/users/{username}/repos"
            params = {
                'sort': 'updated',
                'direction': 'desc',
                'per_page': 100,
                'page': page
            }
            
            response = self._make_request(url, params)
            if not response or response.status_code != 200:
                break
            
            page_repos = response.json()
            if not page_repos:
                break
            
            repos.extend(page_repos)
            page += 1
            
            # Limit to 500 repos max
            if len(repos) >= 500:
                break
        
        # Sort by stars (descending)
        repos.sort(key=lambda x: x.get('stargazers_count', 0), reverse=True)
        return repos[:100]  # Return top 100 repos
    
    def _make_request(self, url, params=None):
        """Make API request with rate limit handling"""
        # Check rate limit
        if self.remaining_requests <= 5:
            wait_time = (self.reset_time - datetime.now()).total_seconds()
            if wait_time > 0:
                print(f"Rate limit low, waiting {wait_time} seconds...")
                time.sleep(min(wait_time + 5, 60))
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            # Update rate limit info
            self.remaining_requests = int(response.headers.get('X-RateLimit-Remaining', 60))
            reset_timestamp = int(response.headers.get('X-RateLimit-Reset', 0))
            if reset_timestamp:
                self.reset_time = datetime.fromtimestamp(reset_timestamp)
            
            return response
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def _calculate_breakdown(self, user_data, repos):
        """Calculate detailed breakdown scores (0-100 each)"""
        breakdown = {}
        
        # 1. Account Maturity (0-10)
        age_days = self._get_account_age(user_data).days
        if age_days < 30:
            breakdown['account_maturity'] = 2
        elif age_days < 90:
            breakdown['account_maturity'] = 5
        elif age_days < 365:
            breakdown['account_maturity'] = 8
        else:
            breakdown['account_maturity'] = 10
        
        # 2. Repository Count (0-15)
        repo_count = len(repos)
        if repo_count == 0:
            breakdown['repo_count'] = 0
        elif repo_count < 5:
            breakdown['repo_count'] = 5
        elif repo_count < 15:
            breakdown['repo_count'] = 10
        else:
            breakdown['repo_count'] = 15
        
        # 3. Language Diversity (0-20)
        languages = self._extract_languages(repos)
        unique_langs = len(set(languages))
        if unique_langs == 0:
            breakdown['language_diversity'] = 0
        elif unique_langs < 3:
            breakdown['language_diversity'] = 8
        elif unique_langs < 6:
            breakdown['language_diversity'] = 15
        else:
            breakdown['language_diversity'] = 20
        
        # 4. Stars Received (0-15)
        total_stars = sum(r.get('stargazers_count', 0) for r in repos)
        if total_stars == 0:
            breakdown['stars_received'] = 0
        elif total_stars < 10:
            breakdown['stars_received'] = 5
        elif total_stars < 50:
            breakdown['stars_received'] = 10
        else:
            breakdown['stars_received'] = 15
        
        # 5. Recent Activity (0-20)
        recent_commits = self._count_recent_commits(repos)
        if recent_commits == 0:
            breakdown['recent_activity'] = 0
        elif recent_commits < 10:
            breakdown['recent_activity'] = 8
        elif recent_commits < 30:
            breakdown['recent_activity'] = 15
        else:
            breakdown['recent_activity'] = 20
        
        # 6. Documentation Quality (0-10)
        has_readme = sum(1 for r in repos if r.get('has_readme', False))
        has_wiki = sum(1 for r in repos if r.get('has_wiki', False))
        
        if has_readme > 0:
            breakdown['documentation_quality'] = min(5 + (has_readme * 0.5), 10)
        else:
            breakdown['documentation_quality'] = 0
        
        # 7. Community Recognition (0-10)
        followers = user_data.get('followers', 0)
        if followers == 0:
            breakdown['community_recognition'] = 0
        elif followers < 10:
            breakdown['community_recognition'] = 3
        elif followers < 50:
            breakdown['community_recognition'] = 6
        else:
            breakdown['community_recognition'] = 10
        
        return breakdown
    
    def _calculate_total_score(self, breakdown):
        """Sum all breakdown components"""
        return sum(breakdown.values())
    
    def _extract_languages(self, repos):
        """Extract all languages used in repos"""
        languages = []
        for repo in repos:
            lang = repo.get('language')
            if lang:
                languages.append(lang)
            
            # Get language stats if available
            if repo.get('languages_url'):
                # Could fetch detailed language breakdown
                pass
        
        # Count frequency
        lang_counts = Counter(languages)
        return dict(lang_counts.most_common())
    
    def _count_recent_commits(self, repos):
        """Count commits in last 90 days (fixed timezone handling)"""
        recent_count = 0
        now = datetime.now()
        
        for repo in repos[:5]:  # Check top 5 repos only
            pushed_at = repo.get('pushed_at')
            if pushed_at:
                try:
                    from dateutil import parser
                    
                    # Parse the date
                    pushed_date = parser.parse(pushed_at)
                    
                    # Remove timezone if present
                    if pushed_date.tzinfo is not None:
                        pushed_date = pushed_date.replace(tzinfo=None)
                    
                    # Check if within 90 days
                    if (now - pushed_date).days < 90:
                        recent_count += 10  # Approximate
                except Exception as e:
                    print(f"Date parsing error in commit: {e}")
                    continue
        
        return min(recent_count, 100)
    
    def _get_account_age(self, user_data):
        """Calculate account age in days (fixed timezone handling)"""
        created = user_data.get('created_at')
        if created:
            try:
                # GitHub API returns ISO format with timezone (e.g., "2020-01-01T00:00:00Z")
                # Parse it and make it timezone-naive for comparison
                from dateutil import parser
                import pytz
                
                # Parse the date
                created_date = parser.parse(created)
                
                # If it has timezone, convert to naive UTC
                if created_date.tzinfo is not None:
                    created_date = created_date.replace(tzinfo=None)
                
                # Get current time as naive UTC
                now = datetime.now()
                
                # Calculate difference
                age = now - created_date
                return age
            except Exception as e:
                print(f"Date parsing error: {e}")
                return timedelta(days=0)
        return timedelta(days=0)
    
    def _cross_verify_skills(self, claimed_skills, github_languages, repos):
        """Cross-verify claimed skills against GitHub evidence"""
        verification = {
            'verified': [],
            'partial': [],
            'unverified': []
        }
        
        if not claimed_skills:
            return verification
        
        # Normalize all skills to lowercase
        github_langs_lower = [lang.lower() for lang in github_languages.keys()]
        
        for skill in claimed_skills:
            skill_lower = skill.lower()
            
            # Direct match in languages
            if skill_lower in github_langs_lower:
                verification['verified'].append(skill)
                continue
            
            # Check for partial matches (e.g., "python" vs "python3")
            partial_match = False
            for lang in github_langs_lower:
                if skill_lower in lang or lang in skill_lower:
                    partial_match = True
                    break
            
            if partial_match:
                verification['partial'].append(skill)
            else:
                # Check repo descriptions/READMEs for skill mentions
                mentioned = self._check_skill_in_repos(skill, repos)
                if mentioned:
                    verification['partial'].append(skill)
                else:
                    verification['unverified'].append(skill)
        
        return verification
    
    def _check_skill_in_repos(self, skill, repos):
        """Check if skill is mentioned in repo descriptions"""
        skill_lower = skill.lower()
        for repo in repos[:10]:  # Check top 10 repos
            desc = repo.get('description', '')
            if desc and skill_lower in desc.lower():
                return True
            
            name = repo.get('name', '')
            if name and skill_lower in name.lower():
                return True
        
        return False
    
    def _check_cache(self, username):
        """Check if we have cached data for this username"""
        cache_file = os.path.join(self.cache_folder, f"{username}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                # Check if cache is fresh (< 7 days)
                cached_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
                if (datetime.now() - cached_time).days < 7:
                    return data
            except:
                pass
        return None
    
    def _save_cache(self, username, data):
        """Save data to cache"""
        cache_file = os.path.join(self.cache_folder, f"{username}.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass
    
    def _empty_result(self, reason):
        """Return empty result structure"""
        return {
            'username': None,
            'github_score': None,
            'breakdown': {},
            'languages_used': {},
            'repo_count': 0,
            'account_age_days': 0,
            'is_new_account': False,
            'error': reason,
            'timestamp': datetime.now().isoformat()
        }