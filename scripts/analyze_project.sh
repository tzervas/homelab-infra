#!/bin/bash

# Function to escape JSON special characters
escape_json() {
    sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g; s/\n/\\n/g; s/\r/\\r/g'
}

# Create a temporary directory for our analysis
TEMP_DIR=$(mktemp -d)
ANALYSIS_FILE="$TEMP_DIR/analysis.txt"

# Gather all information into analysis file
{
    echo "Project Structure:"
    tree -L 3
    echo -e "\n---\n"

    echo "Project Specification:"
    cat docs/specifications/project_specification.yaml
    echo -e "\n---\n"

    echo "Deployment Plan:"
    cat deployment-plan.yaml
    echo -e "\n---\n"

    echo "Modernization Assessment:"
    cat docs/modernization/assessment.md
    echo -e "\n---\n"

    echo "Unified Deployment Workflow:"
    cat docs/deployment/unified-deployment.md
    echo -e "\n---\n"
} > "$ANALYSIS_FILE"

# Generate Claude prompt
PROMPT=$(cat << 'EOF'
Please perform a comprehensive project analysis and create a detailed alignment strategy and refactoring plan. Based on the provided repository content:

1. Project Analysis:
   - Analyze the current architecture and infrastructure setup
   - Identify key components and their relationships
   - Review the deployment workflow and GitOps implementation
   - Evaluate the security measures and compliance status

2. Alignment Strategy:
   - Propose strategies to align all components with best practices
   - Suggest improvements for the GitOps workflow
   - Recommend security enhancements
   - Outline monitoring and observability improvements

3. Refactoring Plan:
   - Create a detailed, phased refactoring roadmap
   - Prioritize changes based on impact and complexity
   - Include specific code and configuration changes needed
   - Provide rollback procedures for each phase

Please provide specific recommendations and code examples where applicable. Consider both immediate improvements and long-term architectural goals.

Repository content:
EOF
)

# Combine prompt with analysis
FINAL_PROMPT="$PROMPT\n\n$(escape_json < "$ANALYSIS_FILE")"

# Write Claude command to a script
echo "claude --dangerously-skip-permissions <<'EOF'
$FINAL_PROMPT
EOF" > run_analysis.sh

chmod +x run_analysis.sh

echo "Analysis script has been created. Run './run_analysis.sh' to execute the analysis."

# Cleanup
rm -rf "$TEMP_DIR"
