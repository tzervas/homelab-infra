import yaml
import os

# Basic script to generate a feature documentation map

def generate_feature_map(directory, output_path):
    feature_map = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                feature_map[file] = os.path.join(root, file)

    with open(output_path, 'w') as yaml_file:
        yaml.dump(feature_map, yaml_file)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate a feature documentation map.')
    parser.add_argument('-o', '--output', required=True, help='Output path for the feature map YAML')
    args = parser.parse_args()

    generate_feature_map('.', args.output)
