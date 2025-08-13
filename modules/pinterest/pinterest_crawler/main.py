import argparse
from pinterest_crawler.pinterest_crawler import PinterestCrawler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-kw", "--keywords", help="keywords as path of file or list of words", nargs='+', default=[])
    parser.add_argument("-o", "--output-dir", help="output dir", default="./io/output", type=str)
    parser.add_argument("-nw", "--number-of-words", help="number of keywords for each search", default=2, type=int)
    parser.add_argument("-mik", "--max-images-per-keyword", help="maximum images per keyword", default=100, type=int)
    parser.add_argument("-mk", "--max-keywords", help="maximum number of keywords to process", default=5, type=int)
    args = parser.parse_args()
    pinterest_crawler = PinterestCrawler(args.output_dir)
    pinterest_crawler(args.keywords, args.number_of_words, args.max_images_per_keyword, args.max_keywords)


if __name__ == "__main__":
    main()
