source .venv/bin/activate && \
python sources/1_nouns_by_frequency/2_generate_flashcards.py && \
python sources/2_adjectives_by_frequency/2_generate_flashcards.py && \
python sources/3_verbs_infinito_by_frequency/2_generate_flashcards.py && \
python sources/4_verbs_presente_by_frequency/2_generate_flashcards.py && \
python sources/5_verbs_passatoprossimo_by_frequency/2_generate_flashcards.py && \
python sources/6_verbs_imperfetto_by_frequency/2_generate_flashcards.py && \
python sources/7_verbs_presenteprogressivo_by_frequency/2_generate_flashcards.py && \
python sources/8_numbers/2_generate_flashcards.py && \
python sources/9_tuttobene/2_generate_flashcards.py && \
python sources/10_vulgarity/2_generate_flashcards.py && \
python sources/11_cils/3_generate_flashcards.py && \
python builder/1_generate_audio.py && \
python builder/2_generate_images.py && \
python builder/3_compress_media.py && \
python builder/4_create_decks.py