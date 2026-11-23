"""Full held-out replication using the already-trained order-44 uniform SFT adapter."""
import json
from pathlib import Path
import full_one_edit as experiment
import report_full_one_edit as paired
import audit_symbolic_finish as symbolic
import eval_empty_route as empty
from eval_repair_sft import read
from prepare_e2_credit_panel import PARENT, WARM
from rescore_v4_side import digest


def main():
    reference = experiment.OUT
    training = PARENT / "verified-repair-sft-1.7B-orders-v1" / "order-44"
    destination = PARENT / "verified-one-edit-full-order44-v1"
    assert (reference / "results.json").is_file()
    new_adapter = training / "uniform/adapter/adapter_model.safetensors"
    original = read(reference / "protocol.json")
    assert digest(new_adapter) != original["adapter"]
    assert read(training / "uniform/budget.json")["tokens"] == read(experiment.DEST / "uniform/budget.json")["tokens"]
    destination.mkdir(exist_ok=True)
    protocol = dict(reference=digest(reference / "protocol.json"), driver=digest(Path(experiment.__file__)),
                    actual_adapter=digest(new_adapter), training_order="44", method="uniform SFT",
                    interpretation="vary only presentation order at training; same tasks, generated-sample seed, selector and decoding budget")
    marker = destination / "replication.json"
    if marker.exists():
        assert read(marker) == protocol
    else:
        with marker.open("x") as f: json.dump(protocol, f, indent=2)
    experiment.OUT = paired.OUT = destination
    experiment.DEST = training
    experiment.main()
    actual = read(destination / "protocol.json")
    assert all(actual[k] == original[k] for k in ("ids","sources","seed","draws","temperature","batch","max_new_tokens","code","scoring","rule"))
    paired.main()
    symbolic.main(destination)
    empty.main(destination)


if __name__=="__main__":
    main()
