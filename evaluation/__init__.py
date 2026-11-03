"""Running models against the bank and scoring them.

exam.py builds what a model sees, budget.py sizes it and says what a model can and cannot be shown,
scoring.py holds the answers and the rules for reading a reply, providers.py and remote.py say who
answers, run.py puts one answerer's pass together and benchmark.py puts several side by side. Nothing here imports the question generators: a harness that shared code with the
generator could agree with it on a mistake.
"""
