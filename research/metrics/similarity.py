import numpy as np
import pandas as pd
from scipy.spatial.distance import cosine, euclidean  # noqa E402


def pairwise_distance(anchor: np.array, positives: np.array, negatives: np.array):
    euclidean_dist_pos = []
    cosine_dist_pos = []
    for pos in positives:
        euclidean_dist_pos.append(euclidean(anchor, pos))
        cosine_dist_pos.append(cosine(anchor, pos))

    euclidean_dist_neg = []
    cosine_dist_neg = []
    for neg in negatives:
        euclidean_dist_neg.append(euclidean(anchor, neg))
        cosine_dist_neg.append(cosine(anchor, neg))

    return {
        "euclidean_pos": np.mean(euclidean_dist_pos),
        "euclidean_neg": np.mean(euclidean_dist_neg),
        "cosine_pos": np.mean(cosine_dist_pos),
        "cosine_neg": np.mean(cosine_dist_neg),
    }

def get_similarity_metrics(
    df_final: pd.DataFrame,
    n_sample: int = 5,
    only_genre: bool = True,
):
    results = []
    df_final["decade"] = (df_final["album_release_date"].dt.year // 10) * 10
    if not only_genre:
        df_final["target"] = df_final["genre"] + df_final["decade"].astype(str)
    else:
        df_final["target"] = df_final["genre"]
    for genre_ in df_final["target"].unique():
        df_genre = df_final[df_final["target"] == genre_]
        df_other_genre = df_final[df_final["target"] != genre_]

        if df_genre.shape[0] < 6:
            continue

        pos_samples = df_genre.sample(n_sample + 1)["embedding"]
        neg_samples = df_other_genre.sample(n_sample)["embedding"]
        dists = pairwise_distance(
            anchor=pos_samples.iloc[0],
            positives=pos_samples.iloc[1:],
            negatives=neg_samples.tolist(),
        )
        results.append(
            {
                "genre": genre_,
                **dists,
            }
        )

    results_df = pd.DataFrame(results)

    euc_rate = (results_df["euclidean_pos"] < results_df["euclidean_neg"]).mean()
    cos_rate = (results_df["cosine_pos"] < results_df["cosine_neg"]).mean()
    return {"euclidian_rate": euc_rate, "cos_rate": cos_rate}
