# Research

1. install deps from `research` group in poetry
2. setup mlflow uri (public ipv4 from `mlflow-vm` in yandex cloud)
3. commit version of code
4. run exp `python commands.py train --trainer.params.max_epochs=1 --model.params.add_bn=True --model.params.embedding_size=32`
