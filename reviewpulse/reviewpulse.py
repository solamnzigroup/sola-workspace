#!/usr/bin/env python3
"""
ReviewPulse - Amazon Review Monitoring & Sentiment Analysis
Built by Sola Ray (https://solamnzigroup.github.io)
"""

import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from collections import Counter
from datetime import datetime
import json
import time
import random
import re
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel

console = Console()

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

MARKETPLACES = {
    'ca': 'amazon.ca',
    'us': 'amazon.com',
    'uk': 'amazon.co.uk',
}


class ReviewPulse:
    def __init__(self, marketplace='ca'):
        self.marketplace = marketplace
        self.base_url = f"https://www.{MARKETPLACES.get(marketplace, 'amazon.ca')}"
        self.session = requests.Session()
        self.reviews = []
        
    def _get_headers(self):
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def fetch_reviews(self, asin, max_pages=5):
        """Fetch reviews for a product ASIN"""
        console.print(f"\n[bold blue]📊 ReviewPulse[/bold blue] - Fetching reviews for [yellow]{asin}[/yellow]")
        console.print(f"   Marketplace: {self.base_url}\n")
        
        all_reviews = []
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Fetching reviews...", total=max_pages)
            
            for page in range(1, max_pages + 1):
                url = f"{self.base_url}/product-reviews/{asin}?pageNumber={page}&sortBy=recent"
                
                try:
                    # Random delay to avoid blocking
                    time.sleep(random.uniform(1.5, 3.0))
                    
                    response = self.session.get(url, headers=self._get_headers(), timeout=15)
                    
                    if response.status_code == 503:
                        console.print(f"[yellow]⚠️  Rate limited on page {page}, waiting...[/yellow]")
                        time.sleep(5)
                        continue
                    
                    if response.status_code != 200:
                        console.print(f"[red]❌ Error fetching page {page}: {response.status_code}[/red]")
                        continue
                    
                    soup = BeautifulSoup(response.text, 'lxml')
                    reviews = self._parse_reviews(soup)
                    
                    if not reviews:
                        console.print(f"[dim]   No more reviews found on page {page}[/dim]")
                        break
                    
                    all_reviews.extend(reviews)
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    console.print(f"[red]❌ Error on page {page}: {str(e)}[/red]")
                    continue
        
        self.reviews = all_reviews
        console.print(f"\n[green]✅ Fetched {len(all_reviews)} reviews[/green]")
        return all_reviews
    
    def _parse_reviews(self, soup):
        """Parse reviews from HTML"""
        reviews = []
        review_divs = soup.select('[data-hook="review"]')
        
        for div in review_divs:
            try:
                # Extract rating
                rating_elem = div.select_one('[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]')
                rating = None
                if rating_elem:
                    rating_text = rating_elem.get_text()
                    match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                    if match:
                        rating = float(match.group(1))
                
                # Extract title
                title_elem = div.select_one('[data-hook="review-title"]')
                title = title_elem.get_text(strip=True) if title_elem else ""
                # Clean up title (remove rating prefix if present)
                title = re.sub(r'^\d+\.\d+ out of \d+ stars?', '', title).strip()
                
                # Extract body
                body_elem = div.select_one('[data-hook="review-body"]')
                body = body_elem.get_text(strip=True) if body_elem else ""
                
                # Extract date
                date_elem = div.select_one('[data-hook="review-date"]')
                date_text = date_elem.get_text(strip=True) if date_elem else ""
                
                # Extract verified purchase
                verified_elem = div.select_one('[data-hook="avp-badge"]')
                verified = verified_elem is not None
                
                # Extract helpful votes
                helpful_elem = div.select_one('[data-hook="helpful-vote-statement"]')
                helpful_text = helpful_elem.get_text(strip=True) if helpful_elem else ""
                helpful_count = 0
                if helpful_text:
                    match = re.search(r'(\d+)', helpful_text)
                    if match:
                        helpful_count = int(match.group(1))
                
                if body:  # Only add if there's actual content
                    reviews.append({
                        'rating': rating,
                        'title': title,
                        'body': body,
                        'date': date_text,
                        'verified': verified,
                        'helpful_votes': helpful_count,
                    })
                    
            except Exception as e:
                continue
        
        return reviews
    
    def analyze_sentiment(self):
        """Analyze sentiment of all reviews"""
        if not self.reviews:
            console.print("[yellow]⚠️  No reviews to analyze. Fetch reviews first.[/yellow]")
            return None
        
        console.print("\n[bold blue]🧠 Analyzing sentiment...[/bold blue]\n")
        
        sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
        sentiment_scores = []
        
        for review in self.reviews:
            text = f"{review['title']} {review['body']}"
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            sentiment_scores.append(polarity)
            
            if polarity > 0.1:
                sentiments['positive'] += 1
                review['sentiment'] = 'positive'
            elif polarity < -0.1:
                sentiments['negative'] += 1
                review['sentiment'] = 'negative'
            else:
                sentiments['neutral'] += 1
                review['sentiment'] = 'neutral'
            
            review['sentiment_score'] = polarity
        
        total = len(self.reviews)
        avg_score = sum(sentiment_scores) / total if total > 0 else 0
        
        analysis = {
            'total_reviews': total,
            'positive': sentiments['positive'],
            'negative': sentiments['negative'],
            'neutral': sentiments['neutral'],
            'positive_pct': round(sentiments['positive'] / total * 100, 1) if total > 0 else 0,
            'negative_pct': round(sentiments['negative'] / total * 100, 1) if total > 0 else 0,
            'neutral_pct': round(sentiments['neutral'] / total * 100, 1) if total > 0 else 0,
            'avg_sentiment_score': round(avg_score, 3),
        }
        
        return analysis
    
    def extract_keywords(self, top_n=20):
        """Extract common keywords and phrases"""
        if not self.reviews:
            return []
        
        console.print("\n[bold blue]🏷️  Extracting keywords...[/bold blue]\n")
        
        # Common words to ignore
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought',
            'used', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'what', 'which', 'who', 'whom', 'this', 'that', 'am', 'is',
            'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
            'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or',
            'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about',
            'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under',
            'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
            'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
            'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't',
            'just', 'don', 'now', 've', 'll', 're', 'm', 'product', 'amazon', 'bought',
            'buy', 'purchase', 'purchased', 'ordered', 'order', 'item', 'review', 'reviews',
            'really', 'very', 'much', 'also', 'get', 'got', 'use', 'using', 'used',
            'one', 'two', 'first', 'would', 'like', 'great', 'good', 'well', 'take',
            'taking', 'took', 'started', 'start', 'since', 'every', 'day', 'days',
            'time', 'times', 'been', 'feel', 'feeling', 'felt', 'think', 'thought',
        }
        
        all_words = []
        for review in self.reviews:
            text = f"{review['title']} {review['body']}".lower()
            words = re.findall(r'\b[a-z]{3,}\b', text)
            words = [w for w in words if w not in stop_words]
            all_words.extend(words)
        
        word_counts = Counter(all_words)
        return word_counts.most_common(top_n)
    
    def get_negative_insights(self):
        """Get insights from negative reviews"""
        if not self.reviews:
            return []
        
        negative_reviews = [r for r in self.reviews if r.get('sentiment') == 'negative']
        
        if not negative_reviews:
            return []
        
        # Extract common complaints
        complaints = []
        for review in negative_reviews:
            complaints.append({
                'title': review['title'],
                'body': review['body'][:200] + '...' if len(review['body']) > 200 else review['body'],
                'rating': review['rating'],
                'helpful_votes': review['helpful_votes'],
            })
        
        # Sort by helpful votes (most impactful complaints first)
        complaints.sort(key=lambda x: x['helpful_votes'], reverse=True)
        
        return complaints[:10]  # Top 10 complaints
    
    def display_report(self):
        """Display a formatted report"""
        analysis = self.analyze_sentiment()
        keywords = self.extract_keywords(15)
        negative_insights = self.get_negative_insights()
        
        if not analysis:
            return
        
        # Header
        console.print(Panel.fit(
            "[bold white]📊 ReviewPulse Analysis Report[/bold white]",
            border_style="blue"
        ))
        
        # Sentiment Summary
        table = Table(title="Sentiment Analysis", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")
        table.add_column("Percentage", justify="right")
        
        table.add_row("Total Reviews", str(analysis['total_reviews']), "")
        table.add_row("✅ Positive", str(analysis['positive']), f"{analysis['positive_pct']}%")
        table.add_row("❌ Negative", str(analysis['negative']), f"{analysis['negative_pct']}%")
        table.add_row("➖ Neutral", str(analysis['neutral']), f"{analysis['neutral_pct']}%")
        table.add_row("Avg Sentiment", str(analysis['avg_sentiment_score']), "(-1 to +1)")
        
        console.print(table)
        
        # Keywords
        if keywords:
            console.print("\n[bold cyan]🏷️  Top Keywords[/bold cyan]")
            keyword_str = ", ".join([f"{word} ({count})" for word, count in keywords[:10]])
            console.print(f"   {keyword_str}")
        
        # Negative Insights
        if negative_insights:
            console.print("\n[bold red]⚠️  Top Complaints (negative reviews by helpfulness)[/bold red]")
            for i, complaint in enumerate(negative_insights[:5], 1):
                console.print(f"\n   {i}. [red]★{complaint['rating']}[/red] - {complaint['title']}")
                console.print(f"      [dim]{complaint['body'][:150]}[/dim]")
        
        return analysis
    
    def export_json(self, filename):
        """Export reviews and analysis to JSON"""
        analysis = self.analyze_sentiment()
        keywords = self.extract_keywords()
        
        export_data = {
            'generated_at': datetime.now().isoformat(),
            'marketplace': self.marketplace,
            'analysis': analysis,
            'keywords': keywords,
            'reviews': self.reviews,
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        console.print(f"\n[green]✅ Exported to {filename}[/green]")


@click.command()
@click.option('--asin', '-a', required=True, help='Amazon product ASIN')
@click.option('--marketplace', '-m', default='ca', help='Marketplace (ca/us/uk)')
@click.option('--pages', '-p', default=5, help='Max pages to fetch')
@click.option('--export', '-e', default=None, help='Export to JSON file')
@click.option('--demo', is_flag=True, help='Run with sample data (for testing)')
def main(asin, marketplace, pages, export, demo):
    """ReviewPulse - Amazon Review Analysis Tool"""
    
    rp = ReviewPulse(marketplace=marketplace)
    
    if demo:
        console.print("\n[yellow]🎭 DEMO MODE - Using sample review data[/yellow]")
        rp.reviews = [
            {'rating': 5, 'title': 'Amazing product!', 'body': 'This magnesium has really helped with my sleep quality. I fall asleep faster and wake up refreshed. Highly recommend for anyone with sleep issues.', 'date': 'January 15, 2026', 'verified': True, 'helpful_votes': 12},
            {'rating': 5, 'title': 'Great for focus', 'body': 'I started taking this for brain fog and it has made a noticeable difference. My concentration is better during work. Quality Canadian product.', 'date': 'January 10, 2026', 'verified': True, 'helpful_votes': 8},
            {'rating': 4, 'title': 'Good but capsules are large', 'body': 'The product works well for my anxiety but the capsules are quite large and hard to swallow. Would prefer smaller capsules. Otherwise great quality.', 'date': 'January 8, 2026', 'verified': True, 'helpful_votes': 5},
            {'rating': 5, 'title': 'Finally sleeping through the night', 'body': 'After trying many sleep supplements, this magnesium l-threonate actually works. No grogginess in the morning. Will definitely repurchase.', 'date': 'January 5, 2026', 'verified': True, 'helpful_votes': 15},
            {'rating': 3, 'title': 'Okay but expensive', 'body': 'The product seems to work but its quite pricey compared to other magnesium supplements. Not sure if the premium is worth it yet.', 'date': 'January 3, 2026', 'verified': True, 'helpful_votes': 3},
            {'rating': 2, 'title': 'Didn\'t notice any difference', 'body': 'I took this for a month and honestly didnt notice any improvement in my sleep or focus. Maybe it works for others but not for me. Disappointed.', 'date': 'December 28, 2025', 'verified': True, 'helpful_votes': 7},
            {'rating': 5, 'title': 'Best magnesium I\'ve tried', 'body': 'I have tried many forms of magnesium and L-threonate is the only one that crosses the blood brain barrier. This product is high quality and Canadian made which I appreciate.', 'date': 'December 25, 2025', 'verified': True, 'helpful_votes': 20},
            {'rating': 4, 'title': 'Helps with stress', 'body': 'Taking this before bed helps me unwind and manage my stress levels. Good product, fast shipping from Amazon.', 'date': 'December 20, 2025', 'verified': True, 'helpful_votes': 4},
            {'rating': 1, 'title': 'Gave me stomach issues', 'body': 'Unfortunately this product gave me an upset stomach and nausea. Had to stop taking it after a few days. Not for everyone I guess.', 'date': 'December 15, 2025', 'verified': True, 'helpful_votes': 9},
            {'rating': 5, 'title': 'Noticeable cognitive improvement', 'body': 'As a software developer, I need to stay sharp. This supplement has noticeably improved my memory and mental clarity. Taking 2 capsules at night.', 'date': 'December 10, 2025', 'verified': True, 'helpful_votes': 11},
        ]
    else:
        rp.fetch_reviews(asin, max_pages=pages)
        if not rp.reviews:
            console.print("\n[red]❌ Amazon blocked the request (robot check).[/red]")
            console.print("[dim]To fetch real reviews, you need:[/dim]")
            console.print("[dim]  • Proxy rotation service (e.g., Bright Data, Oxylabs)[/dim]")
            console.print("[dim]  • Or use Amazon's Product Advertising API[/dim]")
            console.print("[dim]  • Or third-party services (e.g., Rainforest API, Keepa)[/dim]")
            console.print("\n[yellow]💡 Run with --demo to see the tool in action with sample data[/yellow]")
            return
    
    rp.display_report()
    
    if export:
        rp.export_json(export)


if __name__ == '__main__':
    main()
