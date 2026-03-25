from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.search.benchmarking import load_benchmark_spec, run_benchmark, write_reports


class Command(BaseCommand):
    help = "Запускает benchmark поиска по набору контрольных запросов и сохраняет JSON/CSV-отчёты."

    def add_arguments(self, parser):
        parser.add_argument(
            "--spec",
            default=str(Path(settings.BASE_DIR) / "benchmarks" / "search_benchmark.sample.json"),
            help="Путь к JSON-спецификации benchmark-набора.",
        )
        parser.add_argument(
            "--runs",
            type=int,
            default=int(getattr(settings, "SEARCH_BENCHMARK_RUNS", 3)),
            help="Сколько раз повторять каждый кейс в каждом режиме поиска.",
        )
        parser.add_argument(
            "--top-k",
            type=int,
            default=int(getattr(settings, "SEARCH_BENCHMARK_TOP_K", 5)),
            help="Сколько верхних результатов учитывать при оценке качества.",
        )
        parser.add_argument(
            "--output-dir",
            default=str(Path(settings.BASE_DIR) / getattr(settings, "SEARCH_BENCHMARK_OUTPUT_DIR", "var/search_benchmarks")),
            help="Каталог для сохранения отчётов benchmark.",
        )
        parser.add_argument(
            "--no-warmup",
            action="store_true",
            help="Не прогревать Milvus и модели перед замером.",
        )
        parser.add_argument(
            "--with-reranker-warmup",
            action="store_true",
            help="Во время прогрева дополнительно загрузить reranker.",
        )

    def handle(self, *args, **options):
        spec_path = Path(options["spec"])
        if not spec_path.exists():
            raise CommandError(f"Файл спецификации не найден: {spec_path}")
        if int(options["runs"]) <= 0:
            raise CommandError("Параметр --runs должен быть положительным числом.")
        if int(options["top_k"]) <= 0:
            raise CommandError("Параметр --top-k должен быть положительным числом.")

        _, cases = load_benchmark_spec(spec_path)
        if not cases:
            raise CommandError("В benchmark-спецификации нет ни одного кейса.")

        self.stdout.write(f"Загружено benchmark-кейсов: {len(cases)}")
        report = run_benchmark(
            cases=cases,
            runs_per_case=int(options["runs"]),
            top_k_eval=int(options["top_k"]),
            warmup=not bool(options["no_warmup"]),
            include_reranker_in_warmup=bool(options["with_reranker_warmup"]),
        )
        report_paths = write_reports(report, options["output_dir"])

        self.stdout.write("")
        runtime = report.get("runtime") or {}
        if runtime:
            self.stdout.write(f"Runtime: embedding_device={runtime.get('embedding_device')}, fp16={runtime.get('embedding_use_fp16')}, rerank_device={runtime.get('rerank_device')}, model={runtime.get('embedding_model')}")

        self.stdout.write(self.style.SUCCESS("Сводка по режимам поиска:"))
        for row in report["summary"]:
            base = (
                f"- {row['mode']}: mean={row['mean_ms']} ms, median={row['median_ms']} ms, "
                f"p95={row['p95_ms']} ms, avg_results={row['avg_result_count']}, avg_top_score={row['avg_top_score']}"
            )
            if "mrr" in row:
                base += (
                    f", MRR={row['mrr']}, Hits@1={row['hits_at_1']}, Hits@3={row['hits_at_3']}, Hits@5={row['hits_at_5']}"
                )
            self.stdout.write(base)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"JSON-отчёт: {report_paths['json']}"))
        self.stdout.write(self.style.SUCCESS(f"CSV-отчёт: {report_paths['csv']}"))
