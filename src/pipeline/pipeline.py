import ingest
import clean
import transform
import metrics

if __name__ == "__main__":
    ingest.main()
    clean.main()
    transform.main()
    metrics.main()
