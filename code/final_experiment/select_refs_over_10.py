import json
def get_papers_2_refs_doi():
    with open('alt_disruption/final_run_experiment/data/papers_2_refs_doi.json','r') as f:
        papers_2_refs_doi=json.load(f)
    return papers_2_refs_doi


def get_papers_refs(papers_2_refs_doi):
    focal_doi_refs_over_10=set()
    with open(f'alt_disruption/final_run_experiment/results/experimental_papers_DI_and_its_variants.jsonl','r') as f:
        for line in f:
            line = json.loads(line)
            doi=list(line.keys())[0].lower()
            if len(papers_2_refs_doi[doi])>10:
                focal_doi_refs_over_10.add(doi)
    
    with open('alt_disruption/final_run_experiment/data/experimental_with_controls.json') as f2:
        control_doi_refs_over_10=set()
        content=json.load(f2)
        for line in content:
            if line['experimental_doi'].lower() in focal_doi_refs_over_10:
                for ref in line['controls']:
                    ref_doi=ref.get('doi').split('https://doi.org/')[-1].lower()
                    if len(papers_2_refs_doi[ref_doi])>10:
                        control_doi_refs_over_10.add(ref_doi)

    control_social_dois_set=set()
    with open('alt_disruption/final_run_experiment/data/control_papers_altmetric_counts.jsonl','r') as f3:
        for line in f3:
            line=json.loads(line)
            control_social_doi=line.get('doi').lower()
            control_social_dois_set.add(control_social_doi)

    final_control_dois=control_doi_refs_over_10 & control_social_dois_set

    print(len(focal_doi_refs_over_10))
    print(len(control_doi_refs_over_10))
    print(len(control_doi_refs_over_10 & control_social_dois_set))
    return focal_doi_refs_over_10, final_control_dois

def select_data(dois_set,type,index_name):
    wf = open(f'alt_disruption/final_run_experiment/results/select_refs_{type}_papers_{index_name}_and_its_variants.jsonl','w') 
    path=f'alt_disruption/final_run_experiment/results/{type}_papers_{index_name}_and_its_variants.jsonl'
    with open(path,'r') as f:
        for line in f:
            line=json.loads(line)
            doi=list(line.keys())[0].lower()
            if  doi in dois_set:
                json.dump(line,wf)
                wf.write('\n')
                wf.flush()



papers_2_refs_doi=get_papers_2_refs_doi()
focal_doi_refs_over_10, final_control_dois=get_papers_refs(papers_2_refs_doi)
# select_data(focal_doi_refs_over_10,'experimental','DI')
# select_data(focal_doi_refs_over_10,'experimental','SDI')
# select_data(final_control_dois,'control','SDI')
select_data(final_control_dois,'control','DI')
# 'alt_disruption/final_run_experiment/data/experimental_papers_info.json'

# 'alt_disruption/final_run_experiment/data/experimental_with_controls.json'