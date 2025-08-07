import yaml
import os

# Basic script to generate a feature documentation map

def generate_feature_map(directory, output_path):
    feature_map = {}
    # Store paths relative to the base directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                rel_path = os.path.relpath(os.path.join(root, file), directory)
                name = os.path.splitext(rel_path)[0].replace(os.sep, '/')
                # Check for duplicate feature names
                if name in feature_map:
                    # If we have a collision, use the full relative path
                    feature_map[rel_path] = os.path.join(root, file)
                else:
                    feature_map[name] = os.path.join(root, file)
    
    with open(output_path, 'w') as yaml_file:
        yaml.dump(feature_map, yaml_file)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate a feature documentation map.')
    parser.add_argument('-o', '--output', required=True, help='Output path for the feature map YAML')
    args = parser.parse_args()

    generate_feature_map('.', args.output)
