#!venv/bin/python
from argparse import ArgumentParser
from convert import convert_coords_and_segments
from update import update_map_html


def main(args):
    convert_coords_and_segments(src=args.src,
                                tgt_coords=args.tgt_coords,
                                tgt_segs=args.tgt_segs)
    update_map_html(coords=args.tgt_coords + '.json',
                    segs=args.tgt_segs + '.json',
                    tamp=args.tamp,
                    tgt=args.tgt)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Process transport record and update map HTML.")
    parser.add_argument('--src', type=str, default='./data/transport_record.xlsx',
                        help='Path to the source transport record file. (default: ./data/transport_record.xlsx)')
    parser.add_argument('--tgt_coords', type=str, default='./configs/locCoords',
                        help='Path to the location coordinates file. (default: ./configs/locCoords)')
    parser.add_argument('--tgt_segs', type=str, default='./configs/travelSegments',
                        help='Path to the travel segments file. (default: ./configs/travelSegments)')
    parser.add_argument('--tamp', type=str, default='./templates/map_heat16_ds.html',
                        help='Path to the template HTML file. (default: ./templates/map_heat16_ds.html)')
    parser.add_argument('--tgt', type=str, default='./incoming.html',
                        help='Path to the target HTML file. (default: ./incoming.html)')
    main(args=parser.parse_args())
