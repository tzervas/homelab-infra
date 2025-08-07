#!/usr/bin/env python3

import subprocess
import sys
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class BranchInfo:
    name: str
    last_commit: str
    last_author: str
    last_date: datetime
    commit_count: int
    base_branch: Optional[str] = None

def run_git_command(cmd: List[str]) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed: {' '.join(cmd)}")
        logging.error(f"Error output: {e.stderr}")
        sys.exit(1)

def get_all_branches() -> List[str]:
    branches = run_git_command(['git', 'branch', '--format=%(refname:short)']).split('\n')
    return [b for b in branches if b]

def get_branch_info(branch: str) -> BranchInfo:
    # Get last commit info
    commit_info = run_git_command([
        'git', 'log', '-1',
        '--format=%H%n%an%n%aI',
        branch
    ]).split('\n')
    
    # Get commit count
    commit_count = int(run_git_command([
        'git', 'rev-list', '--count', branch
    ]))
    
    # Try to determine base branch
    base_branch = None
    try:
        merge_base = run_git_command(['git', 'merge-base', branch, 'main'])
        base_branch = 'main'
    except subprocess.CalledProcessError:
        pass
    
    return BranchInfo(
        name=branch,
        last_commit=commit_info[0],
        last_author=commit_info[1],
        last_date=datetime.fromisoformat(commit_info[2]),
        commit_count=commit_count,
        base_branch=base_branch
    )

def analyze_branches() -> Dict[str, BranchInfo]:
    branches = get_all_branches()
    branch_info = {}
    
    for branch in branches:
        info = get_branch_info(branch)
        branch_info[branch] = info
        
    return branch_info

def print_analysis(branch_info: Dict[str, BranchInfo]) -> None:
    logging.info("\nBranch Analysis Report")
    logging.info("=" * 80)
    
    for branch, info in sorted(branch_info.items(), key=lambda x: x[1].last_date, reverse=True):
        logging.info(f"\nBranch: {branch}")
        logging.info(f"Last Commit: {info.last_commit[:8]}")
        logging.info(f"Last Author: {info.last_author}")
        logging.info(f"Last Modified: {info.last_date.strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"Commit Count: {info.commit_count}")
        if info.base_branch:
            logging.info(f"Base Branch: {info.base_branch}")
        logging.info("-" * 40)

def main() -> None:
    logging.info("Starting branch analysis...")
    branch_info = analyze_branches()
    print_analysis(branch_info)
    logging.info("\nAnalysis complete!")

if __name__ == "__main__":
    main()
