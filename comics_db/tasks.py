from celery import shared_task

from comics_db.parsers import CloudFilesParser, MarvelAPIParser
from comicsdb.celery import logger

parsers = {
    'CLOUD_FILES': CloudFilesParser,
    'MARVEL_API': MarvelAPIParser
}


@shared_task(bind=True)
def parser_run_task(self, parser_name, init_args):
    logger.info(init_args)
    p = parsers[parser_name](*init_args)
    p.run(self.request.id)
