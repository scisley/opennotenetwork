"""Classifiers package for post classification"""

from app.classifiers.base import BaseClassifier
from app.classifiers.registry import (
    ClassifierRegistry,
    register_classifier
)

# Import all classifier modules to trigger decorator registration
from app.classifiers.climate_misinformation_v1 import ClimateMisinformationV1
from app.classifiers.topic_tagger_v1 import TopicTaggerV1
from app.classifiers.science_domain_v1 import ScienceDomainV1
from app.classifiers.full_fact_v1 import FullFactV1
from app.classifiers.domain_classifier_v1 import DomainClassifierV1
from app.classifiers.partisan_tilt_classifier_v1 import PartisanTiltClassifierV1
from app.classifiers.media_type_v1 import MediaTypeV1
from app.classifiers.tweet_type_v1 import TweetTypeV1
from app.classifiers.clarity_v1 import ClarityV1

__all__ = [
    'BaseClassifier',
    'ClassifierRegistry',
    'register_classifier',
    # Classifier classes
    'ClimateMisinformationV1',
    'TopicTaggerV1',
    'ScienceDomainV1',
    'FullFactV1',
    'DomainClassifierV1',
    'PartisanTiltClassifierV1',
    'MediaTypeV1',
    'TweetTypeV1',
    'ClarityV1',
]