import argparse
import json
import logging

from .collector import Collector
from .core import Config, Store


def main():
    parser = argparse.ArgumentParser(description='TrialWatch persistent BNS collector and local API')
    parser.add_argument('--config', help='JSON config path')
    parser.add_argument('--state-dir', help='Persistent SQLite/PDF directory')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('seed', help='Import the included snapshot without network access (idempotent)')
    sub.add_parser('refresh', help='Run one fresh AWS check and bounded PDF batch')
    sub.add_parser('worker', help='Run refreshes until stopped')
    links = sub.add_parser('validate-links', help='Link each PDF to law profiles and audit association evidence')
    links.add_argument('--output', help='Write the JSON audit to this path')
    serve = sub.add_parser('serve', help='Serve API + demo + scheduled refresh worker')
    serve.add_argument('--host', default='127.0.0.1')
    serve.add_argument('--port', default=8000, type=int)
    serve.add_argument('--interval', type=int, help='Override interval (minimum 30 seconds)')
    serve.add_argument('--no-scheduler', action='store_true', help='API only; run worker separately')
    args = parser.parse_args()
    config = Config.load(args.config, args.state_dir)
    if args.command == 'serve' and args.interval:
        config.interval_seconds = args.interval
        config.__post_init__()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    store = Store(config.state_dir)
    if args.command == 'seed':
        print(json.dumps(store.seed(), indent=2))
    elif args.command == 'validate-links':
        from .law_links import sync_all
        result = sync_all(store)
        text = json.dumps(result, indent=2)
        if args.output:
            from pathlib import Path
            Path(args.output).write_text(text + '\n')
        print(text)
    elif args.command == 'refresh':
        result = Collector(config, store).refresh()
        print(json.dumps(result, indent=2))
        if result['status'] in ('failed', 'busy'):
            raise SystemExit(1)
    elif args.command == 'worker':
        engine = Collector(config, store)
        try:
            engine.schedule()
        except KeyboardInterrupt:
            engine.stop.set()
    else:
        import uvicorn
        from .app import create_app
        # Single process: multi-worker ASGI deployments need a separate worker command.
        uvicorn.run(create_app(config, scheduler=not args.no_scheduler), host=args.host, port=args.port)


if __name__ == '__main__':
    main()
