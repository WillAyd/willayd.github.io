from bs4 import BeautifulSoup
from pelican import signals
from pelican.contents import Page


def add_ogtags_to_default_pages(path, context):
    """
    The SEO plugin for Pelican seems to handle articles but not default
    pages, since the default pages don't have metadata. Here we inject
    a set of default values into those pages.
    """
    if not context.get("article") and not context.get("page"):
        with open(path, encoding="utf8") as html_file:
            soup = BeautifulSoup(html_file, features="html.parser")
        
        og_locale_tag = soup.new_tag(
            "meta", content="en_US", property="og:locale"
        )
        soup.head.append(og_locale_tag)

        og_title_tag = soup.new_tag(
            "meta", content="Will Ayd Personal Blog", property="og:title",
        )

        soup.head.append(og_title_tag)

        og_image_tag = soup.new_tag(
            "meta", content="https://willayd.com/og_logo.png", property="og:image",
        )
        soup.head.append(og_image_tag)

        description = (
            "Will Ayd is an open-source developer and maintainer of the pandas "
            "project. In his personal blog Will writes about C, Python, and "
            "performance optimization."
        )
        og_desc_tag = soup.new_tag(
            "meta", content=description, property="og:description",
        )
        soup.head.append(og_desc_tag)

        with open(path, "w", encoding="utf8") as html_file:
            html_file.write(str(soup))


def register():
    signals.content_written.connect(add_ogtags_to_default_pages)
