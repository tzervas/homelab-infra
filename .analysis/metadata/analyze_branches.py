#!/usr/bin/env python3

import sys
import yaml
from datetime import datetime
import argparse
from typing import Dict, List, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BranchAnalyzer:
    def __init__(self, input_file: str, output_file: str):
        self.input_file = input_file
        self.output_file = output_file
        self.branches: Dict[str, Dict] = {}
        self.branch_categories = {
            'main': [],
            'feature': [],
            'release': [],
            'hotfix': [],
            'cleanup': [],
            'backup': [],
            'fix': [],
            'other': []
        }
        self.recommendations = {
            'preserve': [],
            'consolidate': [],
            'eliminate': [],
            'archive': []
        }

    def parse_branch_data(self) -> None:
        """Parse the branch metadata file."""
        try:
            with open(self.input_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    parts = line.strip().split(' ')
                    if len(parts) >= 3:
                        branch_name = parts[0]
                        commit_hash = parts[1]
                        commit_date = ' '.join(parts[2:])
                        self.branches[branch_name] = {
                            'commit_hash': commit_hash,
                            'commit_date': commit_date
                        }
        except Exception as e:
            logger.error(f"Error parsing branch data: {e}")
            sys.exit(1)

    def categorize_branches(self) -> None:
        """Categorize branches based on their naming patterns."""
        for branch in self.branches:
            if branch == 'main' or branch == 'develop':
                self.branch_categories['main'].append(branch)
            elif branch.startswith(('feature/', 'feat/')):
                self.branch_categories['feature'].append(branch)
            elif branch.startswith('release/'):
                self.branch_categories['release'].append(branch)
            elif branch.startswith('hotfix/'):
                self.branch_categories['hotfix'].append(branch)
            elif branch.startswith('cleanup/'):
                self.branch_categories['cleanup'].append(branch)
            elif branch.startswith('backup/'):
                self.branch_categories['backup'].append(branch)
            elif branch.startswith('fix/'):
                self.branch_categories['fix'].append(branch)
            else:
                self.branch_categories['other'].append(branch)

    def analyze_branches(self) -> None:
        """Analyze branches and make recommendations."""
        # Group related feature branches
        feature_groups = self._group_related_features()
        
        # Analyze each branch for preservation/elimination/archival
        for branch, data in self.branches.items():
            if branch in self.branch_categories['main']:
                self.recommendations['preserve'].append(branch)
                continue

            # Parse the commit date
            try:
                commit_date = datetime.strptime(data['commit_date'].split()[0], '%Y-%m-%d')
                today = datetime.now()
                age_days = (today - commit_date).days
            except Exception:
                age_days = 0

            # Mark branches for consolidation if they're part of a related group
            for group in feature_groups:
                if branch in group and len(group) > 1:
                    if branch not in self.recommendations['consolidate']:
                        self.recommendations['consolidate'].append(branch)
                    break

            # Check if branch should be preserved (active development)
            if age_days < 30:  # Active if modified in last 30 days
                if branch not in self.recommendations['consolidate']:
                    self.recommendations['preserve'].append(branch)
            # Check if branch should be archived (historical value)
            elif branch.startswith('backup/'):
                self.recommendations['archive'].append(branch)
            # Mark remaining old branches for elimination
            else:
                self.recommendations['eliminate'].append(branch)

    def _group_related_features(self) -> List[List[str]]:
        """Group related feature branches based on naming patterns."""
        feature_groups = []
        processed = set()

        for branch in self.branch_categories['feature']:
            if branch in processed:
                continue

            related = [branch]
            branch_topic = branch.split('/')[-1].replace('-', ' ').lower()
            
            # Find related branches
            for other in self.branch_categories['feature']:
                if other != branch and other not in processed:
                    other_topic = other.split('/')[-1].replace('-', ' ').lower()
                    # Check for significant word overlap
                    if len(set(branch_topic.split()) & set(other_topic.split())) >= 2:
                        related.append(other)
                        processed.add(other)

            if len(related) > 1:
                feature_groups.append(related)
            processed.add(branch)

        return feature_groups

    def generate_report(self) -> None:
        """Generate the branch analysis report in YAML format."""
        report = {
            'branch_categories': self.branch_categories,
            'recommendations': self.recommendations,
            'branch_details': self.branches
        }

        try:
            with open(self.output_file, 'w') as f:
                yaml.safe_dump(report, f, default_flow_style=False)
            logger.info(f"Analysis report written to {self.output_file}")
        except Exception as e:
            logger.error(f"Error writing report: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Analyze Git branches and generate YAML report')
    parser.add_argument('-i', '--input', required=True, help='Input file containing branch metadata')
    parser.add_argument('-o', '--output', required=True, help='Output YAML file for analysis report')
    args = parser.parse_args()

    analyzer = BranchAnalyzer(args.input, args.output)
    analyzer.parse_branch_data()
    analyzer.categorize_branches()
    analyzer.analyze_branches()
    analyzer.generate_report()

if __name__ == '__main__':
    main()
