"""Read the existing computed MNIST bundle; never train or invent observations."""

import hashlib
import json
import math
import os
import re
import stat
from decimal import Decimal
from pathlib import Path


class DemoSeedRefused(ValueError):
    """An input, ownership boundary or expected byte identity was not proven."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def jailed(root, relative, *, missing=False):
    """Reject symbolic components within the caller-authorized project root."""
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise DemoSeedRefused("An owned project-relative path is required")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise DemoSeedRefused("Symbolic sample paths are not admitted")
        if not missing and not current.exists():
            raise DemoSeedRefused("Required sample member is absent")
    return current


def read_member(root, relative, *, limit=65536):
    path = jailed(root, relative)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > limit
        ):
            raise DemoSeedRefused("A bounded, singly linked regular member is required")
        chunks = []
        remaining = limit + 1
        while remaining:
            data = os.read(fd, min(65536, remaining))
            if not data:
                break
            chunks.append(data)
            remaining -= len(data)
        result = b"".join(chunks)
        after = os.fstat(fd)
        now = path.stat(follow_symlinks=False)

        def identity(s):
            return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

        if (
            len(result) > limit
            or identity(before) != identity(after)
            or identity(after) != identity(now)
        ):
            raise DemoSeedRefused("Sample member changed while being read")
        return result
    finally:
        os.close(fd)


def _integer(value, *, zero=False):
    if type(value) is not int or value < (0 if zero else 1):
        raise DemoSeedRefused("Invalid integer in computed provenance")
    return value


def _accuracy(value):
    if (
        type(value) not in (float, int)
        or not math.isfinite(value)
        or not 0 <= value <= 1
    ):
        raise DemoSeedRefused("Invalid accuracy in computed provenance")
    return Decimal(str(value))


def load_facts(root):
    """Accept the existing schema and agree with its exact claim/PDF byte hashes."""
    import yaml

    claims_bytes = read_member(root, "claims.json")
    provenance_bytes = read_member(root, "provenance.yaml")
    pdf_bytes = read_member(root, "manuscript.pdf", limit=32 * 1024 * 1024)
    try:

        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise DemoSeedRefused("Duplicate structured input key")
                result[key] = value
            return result

        class UniqueLoader(yaml.SafeLoader):
            def construct_mapping(self, node, deep=False):
                return unique_pairs(
                    (
                        self.construct_object(k, deep=True),
                        self.construct_object(v, deep=True),
                    )
                    for k, v in node.value
                )

        claims = json.loads(claims_bytes, object_pairs_hook=unique_pairs)
        # Use the SafeLoader instance directly so the safe constructor boundary
        # is explicit while retaining duplicate-key rejection at every depth.
        loader = UniqueLoader(provenance_bytes)
        try:
            provenance = loader.get_single_data()
        finally:
            loader.dispose()
        if (
            claims["schema"] != "scitex-clew.claims/v1"
            or provenance["schema"] != "scitex-clew.provenance/v1"
        ):
            raise DemoSeedRefused("Unsupported computed bundle schema")
        dataset = provenance["dataset"]
        if type(dataset["version"]) is not int or (
            dataset["name"],
            dataset["source"],
            dataset["version"],
        ) != ("mnist_784", "OpenML", 1):
            raise DemoSeedRefused("This seed admits only the documented MNIST example")
        split = dataset["split"]
        facts = {
            k: _integer(split[k], zero=k == "seed")
            for k in ("train", "test", "seed", "knn_reference")
        }
        facts["logreg"] = _accuracy(provenance["environment"]["results"]["logreg"])
        facts["knn"] = _accuracy(provenance["environment"]["results"]["knn"])
        session = provenance["sessions"]["sess_train"]
        if session["script"] != "examples/make_example_project_mnist.py":
            raise DemoSeedRefused("Unrecognized example computation provenance")
        outputs = {entry["path"]: entry["hash"] for entry in session["outputs"]}
        if outputs["claims.json"] != digest(claims_bytes) or outputs[
            "manuscript.pdf"
        ] != digest(pdf_bytes):
            raise DemoSeedRefused("Computed output bytes disagree with provenance")
        entries = claims["claims"]
        by_id = {c["claim_id"]: c for c in entries}
        if len(by_id) != len(entries):
            raise DemoSeedRefused("Duplicate claim identifiers")
        patterns = {
            "mnist_logreg_accuracy": r"logistic regression test accuracy = ([0-9.]+)",
            "mnist_knn_accuracy": r"kNN\(k=5\) test accuracy = ([0-9.]+)",
            "mnist_model_comparison": r"logreg minus kNN accuracy = (-?[0-9.]+) on ([0-9]+) held-out images",
        }
        for identifier, pattern in patterns.items():
            claim = by_id[identifier]
            if claim["status"] != "registered" or claim.get("verified_at") is not None:
                raise DemoSeedRefused(
                    "Example seed must not imply independently verified findings"
                )
            match = re.fullmatch(pattern, claim["claim_value"])
            if (
                not match
                or claim["source_file"] != session["script"]
                or claim["file_path"] != "manuscript.pdf"
            ):
                raise DemoSeedRefused("Claim is outside this computed example contract")
            expected = (
                facts["logreg"]
                if identifier == "mnist_logreg_accuracy"
                else facts["knn"]
            )
            if identifier == "mnist_model_comparison":
                expected = facts["logreg"] - facts["knn"]
                if int(match[2]) != facts["test"]:
                    raise DemoSeedRefused(
                        "Claim and provenance test populations disagree"
                    )
            if Decimal(match[1]) != expected:
                raise DemoSeedRefused("Claim and provenance result values disagree")
    except (KeyError, TypeError, ValueError, ArithmeticError, yaml.YAMLError) as exc:
        if isinstance(exc, DemoSeedRefused):
            raise
        raise DemoSeedRefused(
            "Incomplete or malformed computed example bundle"
        ) from exc
    return facts, {
        name: digest(data)
        for name, data in (
            ("claims.json", claims_bytes),
            ("provenance.yaml", provenance_bytes),
            ("manuscript.pdf", pdf_bytes),
        )
    }


def section_text(facts):
    """Render a deliberately modest example, deriving every number from the bundle."""
    a, b = f"{facts['logreg']:.4f}", f"{facts['knn']:.4f}"
    delta = f"{facts['logreg'] - facts['knn']:.4f}"
    return {
        "abstract": (
            "\\begin{abstract}\n"
            "\\pdfbookmark[1]{Abstract}{abstract}\n"
            "This worked MNIST example demonstrates the SciTeX interface; it is not a research finding. "
            f"The existing computed bundle evaluates logistic regression and kNN on {facts['test']:,} "
            f"held-out images, with test accuracies {a} and {b}, respectively. "
            "These registered example claims have not been independently verified. "
            "No model is retrained by opening or seeding this document.\n\\end{abstract}\n"
        ),
        "methods": (
            "\\section{Methods}\n"
            "The existing bundle uses OpenML \\texttt{mnist\\_784}, version 1. "
            f"The recorded split uses {facts['train']:,} training images and {facts['test']:,} held-out "
            f"images with seed {facts['seed']}. The kNN classifier uses $k=5$ and "
            f"{facts['knn_reference']:,} reference images. "
            "The source computation is \\texttt{examples/make\\_example\\_project\\_mnist.py}; "
            "dataset, split and output identities are recorded in \\texttt{provenance.yaml}. "
            "This manuscript is a UI demonstration derived from those existing artifacts.\n"
        ),
        "results": (
            "\\section{Results}\n"
            f"The recorded logistic-regression test accuracy is {a}; the recorded kNN test accuracy "
            f"is {b}. Their accuracy difference (logistic regression minus kNN) is {delta}. "
            "These values come from \\texttt{claims.json} and agree with the recorded provenance. "
            "They are example claims, not independently verified research findings. "
            "No significance test, confidence interval or publication status is asserted.\n"
        ),
    }


def showcase_note(facts, inputs):
    """A separate project note: never replace the author's top-level README."""
    return (
        "# MNIST interface showcase: artifact provenance\n\n"
        "This is a worked UI example, not a research finding or independently verified publication.\n\n"
        "The Writer Abstract, Methods and Results are derived only from the existing "
        "`claims.json`, `provenance.yaml` and matching `manuscript.pdf` bundle. "
        "That bundle records OpenML `mnist_784` version 1, logistic regression and kNN "
        f"(k=5), seed {facts['seed']}, {facts['train']:,} training images and "
        f"{facts['test']:,} held-out images. Its recorded test accuracies are "
        f"{facts['logreg']:.4f} and {facts['knn']:.4f}. These claims are registered, "
        "not independently verified.\n\n"
        "The project template README/scripts describe a separate Torch/UMAP/SVM "
        "workflow. They remain untouched and are not provenance for these displayed "
        "OpenML/logistic-regression/kNN metrics. Seeding does not execute or validate "
        "those scripts, retrain models, download data, or assert that all applications "
        "use one completed analysis pipeline.\n\n"
        "The root PDF is the existing Live Paper example artifact. It is never copied "
        "into Writer compiler output. Writer previews must be compiled through Writer "
        "from its actual section sources in a separately authorized operation. "
        "Bibliography, scripts, other manuscript sections and the top-level README "
        "are not changed by this seed.\n\n"
        "## Input byte identities\n\n"
        + "".join(
            f"- `{name}`: SHA-256 `{value}`\n" for name, value in sorted(inputs.items())
        )
        + "\nAdmission and original section backups are recorded under "
        "`.scitex/showcase/`; any authored section or note blocks automatic replacement.\n"
    )
