from celery import shared_task, group

from comics_db.parsers import *
from comicsdb.celery import logger

parsers = {
    'CLOUD_FILES': CloudFilesParser,
    'MARVEL_API': MarvelAPIParser,
    'MARVEL_API_CREATOR_MERGE': MarvelAPICreatorMergeParser,
    'MARVEL_API_CHARACTER_MERGE': MarvelAPICharacterMergeParser,
    'MARVEL_API_EVENT_MERGE': MarvelAPIEventMergeParser,
    'MARVEL_API_TITLE_MERGE': MarvelAPITitleMergeParser,
    'MARVEL_API_ISSUE_MERGE': MarvelAPIIssueMergeParser
}


@shared_task(bind=True)
def parser_run_task(self, parser_name, init_args):
    logger.info(init_args)
    if parser_name == "FULL_MARVEL_API_MERGE":
        full_marvel_api_merge_task.delay()
    else:
        p = parsers[parser_name](*init_args)
        p.run(self.request.id)


@shared_task(bind=True)
def parser_continue_task(self, run_id):
    run = comics_models.ParserRun.objects.get(id=run_id)
    parser = parsers[run.parser](parser_run=run)
    parser.run(self.request.id)


@shared_task(bind=True)
def full_marvel_api_merge_task(self):
    creator_merge = MarvelAPICreatorMergeParser(queue=True)
    character_merge = MarvelAPICharacterMergeParser(queue=True)
    event_merge = MarvelAPIEventMergeParser(queue=True)
    titles_merge = MarvelAPITitleMergeParser(queue=True)
    issues_merge = MarvelAPIIssueMergeParser(queue=True)
    flow = (
        group([
            parser_continue_task.si(creator_merge.parser_run.id),
            parser_continue_task.si(character_merge.parser_run.id)
        ]) |
        parser_continue_task.si(event_merge.parser_run.id) |
        parser_continue_task.si(titles_merge.parser_run.id) |
        parser_continue_task.si(issues_merge.parser_run.id)
    )
    flow.delay()
