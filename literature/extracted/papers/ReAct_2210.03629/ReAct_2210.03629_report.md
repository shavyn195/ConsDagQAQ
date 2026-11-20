# 论文综合提取报告: ReAct_2210.03629.pdf

---

## 📋 文档元信息

| 属性 | 值 |
|------|----|
| 文件名 | ReAct_2210.03629.pdf |
| 总页数 | 33 |
| 创建工具 | LaTeX with hyperref |
| 图片数量 | 0 |
| 正文字体大小 | 7.0 |

## 📑 目录结构

              - [L8] (p.1) Published as a conference paper at ICLR 2023
  - [L2] (p.1) R
    - [L3] (p.1) E
  - [L2] (p.1) A
    - [L3] (p.1) CT
  - [L2] (p.1) :
  - [L2] (p.1) S
    - [L3] (p.1) YNERGIZING
  - [L2] (p.1) R
    - [L3] (p.1) EASONING
    - [L3] (p.1) AND
  - [L2] (p.1) A
    - [L3] (p.1) CTING
    - [L3] (p.1) IN
  - [L2] (p.1) L
    - [L3] (p.1) ANGUAGE
  - [L2] (p.1) M
    - [L3] (p.1) ODELS
                - [L9] (p.1) Shunyu Yao
                - [L9] (p.1) , Jeffrey Zhao
                - [L9] (p.1) , Dian Yu
                - [L9] (p.1) , Nan Du
                - [L9] (p.1) , Izhak Shafran
                - [L9] (p.1) , Karthik Narasimhan
                - [L9] (p.1) , Yuan Cao
              - [L8] (p.1) Department of Computer Science, Princeton University
              - [L8] (p.1) Google Research, Brain team
              - [L8] (p.1) {shunyuy,karthikn}@princeton.edu
              - [L8] (p.1) {jeffreyzhao,dianyu,dunan,izhak,yuancao}@google.com
      - [L4] (p.1) A
                    - [L11] (p.1) BSTRACT
                - [L9] (p.1) While large language models (LLMs) have demonstrated impressive performance
            - [L7] (p.1) across
            - [L7] (p.1) tasks
            - [L7] (p.1) in
            - [L7] (p.1) language
            - [L7] (p.1) understanding
            - [L7] (p.1) and
            - [L7] (p.1) interactive
            - [L7] (p.1) decision
            - [L7] (p.1) making,
            - [L7] (p.1) their
            - [L7] (p.1) abilities for reasoning (e.g.
            - [L7] (p.1) chain-of-thought prompting) and acting (e.g.
            - [L7] (p.1) action
              - [L8] (p.1) plan generation) have primarily been studied as separate topics.
              - [L8] (p.1) In this paper, we
                - [L9] (p.1) explore the use of LLMs to generate both reasoning traces and task-specific actions
                - [L9] (p.1) in an interleaved manner, allowing for greater synergy between the two:
                - [L9] (p.1) reasoning
            - [L7] (p.1) traces
            - [L7] (p.1) help
            - [L7] (p.1) the
            - [L7] (p.1) model
            - [L7] (p.1) induce,
            - [L7] (p.1) track,
            - [L7] (p.1) and
            - [L7] (p.1) update
            - [L7] (p.1) action
            - [L7] (p.1) plans
            - [L7] (p.1) as
            - [L7] (p.1) well
            - [L7] (p.1) as
            - [L7] (p.1) handle
                - [L9] (p.1) exceptions, while actions allow it to interface with and gather additional information
            - [L7] (p.1) from external sources such as knowledge bases or environments.
            - [L7] (p.1) We apply our
              - [L8] (p.1) approach, named
              - [L8] (p.1) ReAct
              - [L8] (p.1) , to a diverse set of language and decision making tasks
            - [L7] (p.1) and
            - [L7] (p.1) demonstrate
            - [L7] (p.1) its
            - [L7] (p.1) effectiveness
            - [L7] (p.1) over
            - [L7] (p.1) state-of-the-art
            - [L7] (p.1) baselines
            - [L7] (p.1) in
            - [L7] (p.1) addition
            - [L7] (p.1) to
            - [L7] (p.1) improved
            - [L7] (p.1) human
            - [L7] (p.1) interpretability
            - [L7] (p.1) and
            - [L7] (p.1) trustworthiness.
            - [L7] (p.1) Concretely,
            - [L7] (p.1) on
            - [L7] (p.1) question
              - [L8] (p.1) answering (HotpotQA) and fact verification (Fever),
              - [L8] (p.1) ReAct
              - [L8] (p.1) overcomes prevalent
            - [L7] (p.1) issues
            - [L7] (p.1) of
            - [L7] (p.1) hallucination
            - [L7] (p.1) and
            - [L7] (p.1) error
            - [L7] (p.1) propagation
            - [L7] (p.1) in
            - [L7] (p.1) chain-of-thought
            - [L7] (p.1) reasoning
            - [L7] (p.1) by
              - [L8] (p.1) interacting with a simple Wikipedia API, and generating human-like task-solving
            - [L7] (p.1) trajectories
            - [L7] (p.1) that
            - [L7] (p.1) are
            - [L7] (p.1) more
            - [L7] (p.1) interpretable
            - [L7] (p.1) than
            - [L7] (p.1) baselines
            - [L7] (p.1) without
            - [L7] (p.1) reasoning
            - [L7] (p.1) traces.
            - [L7] (p.1) Furthermore,
            - [L7] (p.1) on
            - [L7] (p.1) two
            - [L7] (p.1) interactive
            - [L7] (p.1) decision
            - [L7] (p.1) making
            - [L7] (p.1) benchmarks
            - [L7] (p.1) (ALFWorld
            - [L7] (p.1) and
              - [L8] (p.1) WebShop),
              - [L8] (p.1) ReAct
              - [L8] (p.1) outperforms imitation and reinforcement learning methods by
                - [L9] (p.1) an absolute success rate of 34% and 10% respectively, while being prompted with
              - [L8] (p.1) only one or two in-context examples.
      - [L4] (p.1) 1
      - [L4] (p.1) I
                    - [L11] (p.1) NTRODUCTION
                - [L9] (p.1) A unique feature of human intelligence is the ability to seamlessly combine task-oriented actions with
                - [L9] (p.1) verbal reasoning (or inner speech,
                - [L9] (p.1) Alderson-Day & Fernyhough, 2015), which has been theorized to
              - [L8] (p.1) play an important role in human cognition for enabling self-regulation or strategization (Vygotsky,
              - [L8] (p.1) 1987; Luria, 1965; Fernyhough, 2010) and maintaining a working memory (Baddeley, 1992).
              - [L8] (p.1) Con-
            - [L7] (p.1) sider the example of cooking up a dish in the kitchen.
            - [L7] (p.1) Between any two specific actions, we may
                - [L9] (p.1) reason in language in order to track progress (“now that everything is cut, I should heat up the pot of
              - [L8] (p.1) water”), to handle exceptions or adjust the plan according to the situation (“I don’t have salt, so let
                - [L9] (p.1) me use soy sauce and pepper instead”), and to realize when external information is needed (“how do
            - [L7] (p.1) I prepare dough?
            - [L7] (p.1) Let me search on the Internet”).
            - [L7] (p.1) We may also act (open a cookbook to read the
              - [L8] (p.1) recipe, open the fridge, check ingredients) to support the reasoning and to answer questions (“What
              - [L8] (p.1) dish can I make right now?”).
              - [L8] (p.1) This tight synergy between “acting” and “reasoning” allows humans
              - [L8] (p.1) to learn new tasks quickly and perform robust decision making or reasoning, even under previously
              - [L8] (p.1) unseen circumstances or facing information uncertainties.
                - [L9] (p.1) Recent results have hinted at the possibility of combining verbal reasoning with interactive decision
            - [L7] (p.1) making in autonomous systems.
            - [L7] (p.1) On one hand, properly prompted large language models (LLMs)
            - [L7] (p.1) have
            - [L7] (p.1) demonstrated
            - [L7] (p.1) emergent
            - [L7] (p.1) capabilities
            - [L7] (p.1) to
            - [L7] (p.1) carry
            - [L7] (p.1) out
            - [L7] (p.1) several
            - [L7] (p.1) steps
            - [L7] (p.1) of
            - [L7] (p.1) reasoning
            - [L7] (p.1) traces
            - [L7] (p.1) to
            - [L7] (p.1) derive
                        - [L13] (p.1) Work during Google internship.
                        - [L13] (p.1) Projet page with code:
                        - [L13] (p.1) https://react-lm.github.io/
                        - [L13] (p.1) .
              - [L8] (p.1) 1
- [L1] (p.1) arXiv:2210.03629v3  [cs.CL]  10 Mar 2023
              - [L8] (p.2) Published as a conference paper at ICLR 2023
          - [L6] (p.2) �
          - [L6] (p.2) �
            - [L7] (p.2) Figure
            - [L7] (p.2) 1:
            - [L7] (p.2) (1)
            - [L7] (p.2) Comparison
            - [L7] (p.2) of
            - [L7] (p.2) 4
            - [L7] (p.2) prompting
            - [L7] (p.2) methods,
            - [L7] (p.2) (a)
              - [L8] (p.2) Standard
            - [L7] (p.2) ,
            - [L7] (p.2) (b)
            - [L7] (p.2) Chain-of-thought
            - [L7] (p.2) (
              - [L8] (p.2) CoT
            - [L7] (p.2) ,
                - [L9] (p.2) Reason Only), (c)
              - [L8] (p.2) Act
                - [L9] (p.2) -only, and (d)
              - [L8] (p.2) ReAct
                - [L9] (p.2) (Reason+Act), solving a HotpotQA (Yang et al., 2018)
                - [L9] (p.2) question.
                - [L9] (p.2) (2) Comparison of (a)
              - [L8] (p.2) Act
                - [L9] (p.2) -only and (b)
              - [L8] (p.2) ReAct
                - [L9] (p.2) prompting to solve an AlfWorld (Shridhar
                - [L9] (p.2) et al., 2020b) game.
                - [L9] (p.2) In both domains, we omit in-context examples in the prompt, and only show task
              - [L8] (p.2) solving trajectories generated by the model (Act, Thought) and the environment (Obs).
            - [L7] (p.2) answers
            - [L7] (p.2) from
            - [L7] (p.2) questions
            - [L7] (p.2) in
            - [L7] (p.2) arithmetic,
            - [L7] (p.2) commonsense,
            - [L7] (p.2) and
            - [L7] (p.2) symbolic
            - [L7] (p.2) reasoning
            - [L7] (p.2) tasks
            - [L7] (p.2) (Wei
            - [L7] (p.2) et
            - [L7] (p.2) al.,
            - [L7] (p.2) 2022).
            - [L7] (p.2) However,
            - [L7] (p.2) this
            - [L7] (p.2) “chain-of-thought”
            - [L7] (p.2) reasoning
            - [L7] (p.2) is
            - [L7] (p.2) a
            - [L7] (p.2) static
            - [L7] (p.2) black
            - [L7] (p.2) box,
            - [L7] (p.2) in
            - [L7] (p.2) that
            - [L7] (p.2) the
            - [L7] (p.2) model
            - [L7] (p.2) uses
            - [L7] (p.2) its
            - [L7] (p.2) own
            - [L7] (p.2) internal
            - [L7] (p.2) representations
            - [L7] (p.2) to
            - [L7] (p.2) generate
            - [L7] (p.2) thoughts
            - [L7] (p.2) and
            - [L7] (p.2) is
            - [L7] (p.2) not
            - [L7] (p.2) grounded
            - [L7] (p.2) in
            - [L7] (p.2) the
            - [L7] (p.2) external
            - [L7] (p.2) world,
              - [L8] (p.2) which limits its ability to reason reactively or update its knowledge.
              - [L8] (p.2) This can lead to issues like fact
            - [L7] (p.2) hallucination and error propagation over the reasoning process (Figure 1 (1b)).
            - [L7] (p.2) On the other hand,
                - [L9] (p.2) recent work has explored the use of pre-trained language models for planning and acting in interactive
            - [L7] (p.2) environments (Ahn et al., 2022; Nakano et al., 2021; Yao et al., 2020; Huang et al., 2022a), with
            - [L7] (p.2) a focus on predicting actions via language priors.
            - [L7] (p.2) These approaches usually convert multi-modal
              - [L8] (p.2) observations into text, use a language model to generate domain-specific actions or plans, and then
                - [L9] (p.2) use a controller to choose or execute them.
                - [L9] (p.2) However, they do not employ language models to reason
            - [L7] (p.2) abstractly about high-level goals or maintain a working memory to support acting, barring Huang
            - [L7] (p.2) et al. (2022b) who perform a limited form of verbal reasoning to reiterate spatial facts about the
                - [L9] (p.2) current state.
                - [L9] (p.2) Beyond such simple embodied tasks to interact with a few blocks, there have not been
                - [L9] (p.2) studies on how reasoning and acting can be combined in a synergistic manner for general task solving,
              - [L8] (p.2) and if such a combination can bring systematic benefits compared to reasoning or acting alone.
                - [L9] (p.2) In this work, we present
              - [L8] (p.2) ReAct
                - [L9] (p.2) , a general paradigm to combine reasoning and acting with language
            - [L7] (p.2) models
            - [L7] (p.2) for
            - [L7] (p.2) solving
            - [L7] (p.2) diverse
            - [L7] (p.2) language
            - [L7] (p.2) reasoning
            - [L7] (p.2) and
            - [L7] (p.2) decision
            - [L7] (p.2) making
            - [L7] (p.2) tasks
            - [L7] (p.2) (Figure
            - [L7] (p.2) 1).
              - [L8] (p.2) ReAct
            - [L7] (p.2) prompts
            - [L7] (p.2) LLMs
            - [L7] (p.2) to
            - [L7] (p.2) generate
            - [L7] (p.2) both
            - [L7] (p.2) verbal
            - [L7] (p.2) reasoning
            - [L7] (p.2) traces
            - [L7] (p.2) and
            - [L7] (p.2) actions
            - [L7] (p.2) pertaining
            - [L7] (p.2) to
            - [L7] (p.2) a
            - [L7] (p.2) task
            - [L7] (p.2) in
            - [L7] (p.2) an
              - [L8] (p.2) interleaved manner, which allows the model to perform dynamic reasoning to create, maintain, and
              - [L8] (p.2) adjust high-level plans for acting (reason to act), while also interact with the external environments
              - [L8] (p.2) (e.g. Wikipedia) to incorporate additional information into reasoning (act to reason).
              - [L8] (p.2) 2
              - [L8] (p.3) Published as a conference paper at ICLR 2023
                - [L9] (p.3) We conduct empirical evaluations of
              - [L8] (p.3) ReAct
                - [L9] (p.3) and state-of-the-art baselines on four diverse benchmarks:
            - [L7] (p.3) question
            - [L7] (p.3) answering
            - [L7] (p.3) (HotPotQA,
            - [L7] (p.3) Yang
            - [L7] (p.3) et
            - [L7] (p.3) al.,
            - [L7] (p.3) 2018),
            - [L7] (p.3) fact
            - [L7] (p.3) verification
            - [L7] (p.3) (Fever,
            - [L7] (p.3) Thorne
            - [L7] (p.3) et
            - [L7] (p.3) al.,
            - [L7] (p.3) 2018),
            - [L7] (p.3) text-based
            - [L7] (p.3) game
            - [L7] (p.3) (ALFWorld,
            - [L7] (p.3) Shridhar
            - [L7] (p.3) et
            - [L7] (p.3) al.,
            - [L7] (p.3) 2020b),
            - [L7] (p.3) and
            - [L7] (p.3) webpage
            - [L7] (p.3) navigation
            - [L7] (p.3) (WebShop,
            - [L7] (p.3) Yao
              - [L8] (p.3) et al., 2022).
              - [L8] (p.3) For HotPotQA and Fever, with access to a Wikipedia API that the model can interact
              - [L8] (p.3) with,
              - [L8] (p.3) ReAct
              - [L8] (p.3) outperforms vanilla action generation models while being competitive with chain-of-
            - [L7] (p.3) thought reasoning (
              - [L8] (p.3) CoT
            - [L7] (p.3) ) (Wei et al., 2022).
            - [L7] (p.3) The best approach overall is a combination of
              - [L8] (p.3) ReAct
            - [L7] (p.3) and
              - [L8] (p.3) CoT
            - [L7] (p.3) that
            - [L7] (p.3) allows
            - [L7] (p.3) for
            - [L7] (p.3) the
            - [L7] (p.3) use
            - [L7] (p.3) of
            - [L7] (p.3) both
            - [L7] (p.3) internal
            - [L7] (p.3) knowledge
            - [L7] (p.3) and
            - [L7] (p.3) externally
            - [L7] (p.3) obtained
            - [L7] (p.3) information
            - [L7] (p.3) during reasoning.
            - [L7] (p.3) On ALFWorld and WebShop,
            - [L7] (p.3) two or even one-shot
              - [L8] (p.3) ReAct
            - [L7] (p.3) prompting is able
            - [L7] (p.3) to outperform imitation or reinforcement learning methods trained with
              - [L8] (p.3) 10
              - [L8] (p.3) ∼
              - [L8] (p.3) 10
            - [L7] (p.3) task instances,
              - [L8] (p.3) with an absolute improvement of 34% and 10% in success rates respectively.
              - [L8] (p.3) We also demonstrate
              - [L8] (p.3) the importance of sparse, versatile reasoning in decision making by showing consistent advantages
            - [L7] (p.3) over controlled baselines with actions only.
            - [L7] (p.3) Besides general applicability and performance boost,
              - [L8] (p.3) the combination of reasoning and acting also contributes to model interpretability, trustworthiness,
              - [L8] (p.3) and diagnosability across all domains, as humans can readily distinguish information from model’s
              - [L8] (p.3) internal knowledge versus external environments, as well as inspect reasoning traces to understand
              - [L8] (p.3) the decision basis of model actions.
            - [L7] (p.3) To summarize, our key contributions are the following:
            - [L7] (p.3) (1) we introduce
              - [L8] (p.3) ReAct
            - [L7] (p.3) , a novel prompt-
                - [L9] (p.3) based paradigm to synergize reasoning and acting in language models for general task solving; (2) we
                - [L9] (p.3) perform extensive experiments across diverse benchmarks to showcase the advantage of
              - [L8] (p.3) ReAct
                - [L9] (p.3) in a
              - [L8] (p.3) few-shot learning setup over prior approaches that perform either reasoning or action generation in
                - [L9] (p.3) isolation; (3) we present systematic ablations and analysis to understand the importance of acting in
                - [L9] (p.3) reasoning tasks, and reasoning in interactive tasks; (4) we analyze the limitations of
              - [L8] (p.3) ReAct
                - [L9] (p.3) under the
                - [L9] (p.3) prompting setup (i.e. limited support of reasoning and acting behaviors), and perform initial finetuning
            - [L7] (p.3) experiments showing the potential of
              - [L8] (p.3) ReAct
            - [L7] (p.3) to improve with additional training data.
            - [L7] (p.3) Scaling up
              - [L8] (p.3) ReAct
            - [L7] (p.3) to train and operate on more tasks and combining it with complementary paradigms like
              - [L8] (p.3) reinforcement learning could further unlock the potential of large language models.
      - [L4] (p.3) 2
      - [L4] (p.3) R
                    - [L11] (p.3) E
      - [L4] (p.3) A
                    - [L11] (p.3) C T
      - [L4] (p.3) :
      - [L4] (p.3) S
                    - [L11] (p.3) YNERGIZING
      - [L4] (p.3) R
                    - [L11] (p.3) E
                    - [L11] (p.3) ASONING
      - [L4] (p.3) +
      - [L4] (p.3) A
                    - [L11] (p.3) CT
                    - [L11] (p.3) ING
            - [L7] (p.3) Consider
            - [L7] (p.3) a
            - [L7] (p.3) general
            - [L7] (p.3) setup
            - [L7] (p.3) of
            - [L7] (p.3) an
            - [L7] (p.3) agent
            - [L7] (p.3) interacting
            - [L7] (p.3) with
            - [L7] (p.3) an
            - [L7] (p.3) environment
            - [L7] (p.3) for
            - [L7] (p.3) task
            - [L7] (p.3) solving.
            - [L7] (p.3) At
            - [L7] (p.3) time
            - [L7] (p.3) step
              - [L8] (p.3) t
            - [L7] (p.3) , an agent receives an observation
              - [L8] (p.3) o
              - [L8] (p.3) ∈O
            - [L7] (p.3) from the environment and takes an action
              - [L8] (p.3) a
              - [L8] (p.3) ∈A
            - [L7] (p.3) following some policy
              - [L8] (p.3) π
              - [L8] (p.3) (
              - [L8] (p.3) a
              - [L8] (p.3) |
              - [L8] (p.3) c
              - [L8] (p.3) )
            - [L7] (p.3) , where
              - [L8] (p.3) c
              - [L8] (p.3) = (
              - [L8] (p.3) o
              - [L8] (p.3) , a
              - [L8] (p.3) ,
              - [L8] (p.3) · · ·
              - [L8] (p.3) , o
              - [L8] (p.3) , a
              - [L8] (p.3) , o
              - [L8] (p.3) )
            - [L7] (p.3) is the
            - [L7] (p.3) context
            - [L7] (p.3) to the agent.
                - [L9] (p.3) Learning a policy is challenging when the mapping
              - [L8] (p.3) c
              - [L8] (p.3) �→
              - [L8] (p.3) a
                - [L9] (p.3) is highly implicit and requires extensive
            - [L7] (p.3) computation.
            - [L7] (p.3) For example, the agent shown in Figure 1(1c) is unable to generate the correct final
            - [L7] (p.3) action
            - [L7] (p.3) (Act
            - [L7] (p.3) 4)
            - [L7] (p.3) to
            - [L7] (p.3) finish
            - [L7] (p.3) the
            - [L7] (p.3) QA
            - [L7] (p.3) task
            - [L7] (p.3) as
            - [L7] (p.3) it
            - [L7] (p.3) requires
            - [L7] (p.3) complex
            - [L7] (p.3) reasoning
            - [L7] (p.3) over
            - [L7] (p.3) the
            - [L7] (p.3) trajectory
            - [L7] (p.3) context
                - [L9] (p.3) (Question, Act 1-3, Obs 1-3).
                - [L9] (p.3) Similarly, the agent shown in Figure 1(2a) fails to comprehend from the
              - [L8] (p.3) context that sinkbasin 1 does not contain peppershaker 1, thus keep producing hallucinating actions.
            - [L7] (p.3) The idea of
              - [L8] (p.3) ReAct
            - [L7] (p.3) is simple:
            - [L7] (p.3) we augment the agent’s action space to
              - [L8] (p.3) ˆ
              - [L8] (p.3) A
              - [L8] (p.3) =
              - [L8] (p.3) A ∪L
            - [L7] (p.3) , where
              - [L8] (p.3) L
            - [L7] (p.3) is the
              - [L8] (p.3) space of language.
              - [L8] (p.3) An action
              - [L8] (p.3) ˆ
              - [L8] (p.3) a
              - [L8] (p.3) ∈L
              - [L8] (p.3) in the language space, which we will refer to as a
              - [L8] (p.3) thought
              - [L8] (p.3) or a
              - [L8] (p.3) reasoning trace
              - [L8] (p.3) , does not affect the external environment, thus leading to no observation feedback.
              - [L8] (p.3) Instead, a thought
              - [L8] (p.3) ˆ
              - [L8] (p.3) a
              - [L8] (p.3) aims to compose useful information by reasoning over the current context
              - [L8] (p.3) c
              - [L8] (p.3) ,
              - [L8] (p.3) and update the context
              - [L8] (p.3) c
              - [L8] (p.3) = (
              - [L8] (p.3) c
              - [L8] (p.3) ,
              - [L8] (p.3) ˆ
              - [L8] (p.3) a
              - [L8] (p.3) )
              - [L8] (p.3) to support future reasoning or acting.
              - [L8] (p.3) As shown in Figure 1,
              - [L8] (p.3) there could be various types of useful thoughts, e.g. decomposing task goals and create action plans
              - [L8] (p.3) (2b, Act 1; 1d, Thought 1), injecting commonsense knowledge relevant to task solving (2b, Act 1),
                - [L9] (p.3) extracting important parts from observations (1d, Thought2, 4), track progress and transit action plans
              - [L8] (p.3) (2b, Act 8), handle exceptions and adjust action plans (1d, Thought 3), and so on.
              - [L8] (p.3) However, as the language space
              - [L8] (p.3) L
              - [L8] (p.3) is unlimited, learning in this augmented action space is difficult
            - [L7] (p.3) and
            - [L7] (p.3) requires
            - [L7] (p.3) strong
            - [L7] (p.3) language
            - [L7] (p.3) priors.
            - [L7] (p.3) In
            - [L7] (p.3) this
            - [L7] (p.3) paper,
            - [L7] (p.3) we
            - [L7] (p.3) mainly
            - [L7] (p.3) focus
            - [L7] (p.3) on
            - [L7] (p.3) the
            - [L7] (p.3) setup
            - [L7] (p.3) where
            - [L7] (p.3) a
            - [L7] (p.3) frozen
                - [L9] (p.3) large language model, PaLM-540B (Chowdhery et al., 2022)
                - [L9] (p.3) , is prompted with few-shot in-context
                - [L9] (p.3) examples to generate both domain-specific actions and free-form language thoughts for task solving
            - [L7] (p.3) (Figure
            - [L7] (p.3) 1
            - [L7] (p.3) (1d),
            - [L7] (p.3) (2b)).
            - [L7] (p.3) Each
            - [L7] (p.3) in-context
            - [L7] (p.3) example
            - [L7] (p.3) is
            - [L7] (p.3) a
            - [L7] (p.3) human
            - [L7] (p.3) trajectory
            - [L7] (p.3) of
            - [L7] (p.3) actions,
            - [L7] (p.3) thoughts,
            - [L7] (p.3) and
                - [L9] (p.3) environment observations to solve a task instance (see Appendix C). For the tasks where reasoning is
              - [L8] (p.3) of primary importance (Figure 1(1)), we alternate the generation of thoughts and actions so that the
                - [L9] (p.3) task-solving trajectory consists of multiple thought-action-observation steps.
                - [L9] (p.3) In contrast, for decision
              - [L8] (p.3) making tasks that potentially involve a large number of actions (Figure 1(2)), thoughts only need to
                        - [L13] (p.3) We show some GPT-3 (Brown et al., 2020) results in Appendix A.1, which outperforms PaLM-540B.
              - [L8] (p.3) 3
              - [L8] (p.4) Published as a conference paper at ICLR 2023
                - [L9] (p.4) appear sparsely in the most relevant positions of a trajectory, so we let the language model decide the
              - [L8] (p.4) asynchronous occurrence of thoughts and actions for itself.
                - [L9] (p.4) Since decision making and reasoning capabilities are integrated into a large language model,
              - [L8] (p.4) ReAct
            - [L7] (p.4) enjoys
            - [L7] (p.4) several
            - [L7] (p.4) unique
            - [L7] (p.4) features:
              - [L8] (p.4) A)
              - [L8] (p.4) Intuitive
              - [L8] (p.4) and
              - [L8] (p.4) easy
              - [L8] (p.4) to
              - [L8] (p.4) design
            - [L7] (p.4) :
            - [L7] (p.4) Designing
              - [L8] (p.4) ReAct
            - [L7] (p.4) prompts
            - [L7] (p.4) is
                - [L9] (p.4) straightforward as human annotators just type down their thoughts in language on top of their actions
                - [L9] (p.4) taken.
                - [L9] (p.4) No ad-hoc format choice, thought design, or example selection is used in this paper.
                - [L9] (p.4) We detail
                - [L9] (p.4) prompt design for each task in Sections 3 and 4.
              - [L8] (p.4) B) General and flexible
                - [L9] (p.4) :
                - [L9] (p.4) Due to the flexible thought
            - [L7] (p.4) space
            - [L7] (p.4) and
            - [L7] (p.4) thought-action
            - [L7] (p.4) occurrence
            - [L7] (p.4) format,
              - [L8] (p.4) ReAct
            - [L7] (p.4) works
            - [L7] (p.4) for
            - [L7] (p.4) diverse
            - [L7] (p.4) tasks
            - [L7] (p.4) with
            - [L7] (p.4) distinct
            - [L7] (p.4) action
            - [L7] (p.4) spaces and reasoning needs, including but not limited to QA, fact verification, text game, and web
              - [L8] (p.4) navigation.
              - [L8] (p.4) C) Performant and robust
              - [L8] (p.4) :
              - [L8] (p.4) ReAct
              - [L8] (p.4) shows strong generalization to new task instances
                - [L9] (p.4) while learning solely from one to six in-context examples, consistently outperforming baselines with
            - [L7] (p.4) only reasoning or acting across different domains.
            - [L7] (p.4) We also show in Section 3 additional benefits
                - [L9] (p.4) when finetuning is enabled, and in Section 4 how
              - [L8] (p.4) ReAct
                - [L9] (p.4) performance is robust to prompt selections.
              - [L8] (p.4) D) Human aligned and controllable
                - [L9] (p.4) :
              - [L8] (p.4) ReAct
                - [L9] (p.4) promises an interpretable sequential decision making
                - [L9] (p.4) and reasoning process where humans can easily inspect reasoning and factual correctness.
                - [L9] (p.4) Moreover,
            - [L7] (p.4) humans can also control or correct the agent behavior on the go by thought editing,
            - [L7] (p.4) as shown in
              - [L8] (p.4) Figure 5 in Section 4.
      - [L4] (p.4) 3
      - [L4] (p.4) K
                    - [L11] (p.4) NOWLEDGE
      - [L4] (p.4) -I
                    - [L11] (p.4) NTENSIVE
      - [L4] (p.4) R
                    - [L11] (p.4) EASONING
      - [L4] (p.4) T
                    - [L11] (p.4) ASKS
            - [L7] (p.4) We
            - [L7] (p.4) begin
            - [L7] (p.4) with
            - [L7] (p.4) knowledge-intensive
            - [L7] (p.4) reasoning
            - [L7] (p.4) tasks
            - [L7] (p.4) like
            - [L7] (p.4) multi-hop
            - [L7] (p.4) question
            - [L7] (p.4) answering
            - [L7] (p.4) and
            - [L7] (p.4) fact
            - [L7] (p.4) verification.
            - [L7] (p.4) As
            - [L7] (p.4) shown
            - [L7] (p.4) in
            - [L7] (p.4) Figure
            - [L7] (p.4) 1(1d),
            - [L7] (p.4) by
            - [L7] (p.4) interacting
            - [L7] (p.4) with
            - [L7] (p.4) a
            - [L7] (p.4) Wikipedia
            - [L7] (p.4) API,
              - [L8] (p.4) ReAct
            - [L7] (p.4) is
            - [L7] (p.4) able
            - [L7] (p.4) to
            - [L7] (p.4) retrieve information to support reasoning, while also use reasoning to target what to retrieve next,
              - [L8] (p.4) demonstrating a synergy of reasoning and acting.
              - [L8] (p.4) 3.1
              - [L8] (p.4) S
                                - [L17] (p.4) ETUP
              - [L8] (p.4) Domains
            - [L7] (p.4) We
            - [L7] (p.4) consider
            - [L7] (p.4) two
            - [L7] (p.4) datasets
            - [L7] (p.4) challenging
            - [L7] (p.4) knowledge
            - [L7] (p.4) retrieval
            - [L7] (p.4) and
            - [L7] (p.4) reasoning:
            - [L7] (p.4) (1)
            - [L7] (p.4) Hot-
            - [L7] (p.4) PotQA
            - [L7] (p.4) (Yang
            - [L7] (p.4) et
            - [L7] (p.4) al.,
            - [L7] (p.4) 2018),
            - [L7] (p.4) a
            - [L7] (p.4) multi-hop
            - [L7] (p.4) question
            - [L7] (p.4) answering
            - [L7] (p.4) benchmark
            - [L7] (p.4) that
            - [L7] (p.4) requires
            - [L7] (p.4) reasoning
            - [L7] (p.4) over
            - [L7] (p.4) two
            - [L7] (p.4) or
            - [L7] (p.4) more
            - [L7] (p.4) Wikipedia
            - [L7] (p.4) passages,
            - [L7] (p.4) and
            - [L7] (p.4) (2)
            - [L7] (p.4) FEVER
            - [L7] (p.4) (Thorne
            - [L7] (p.4) et
            - [L7] (p.4) al.,
            - [L7] (p.4) 2018),
            - [L7] (p.4) a
            - [L7] (p.4) fact
            - [L7] (p.4) verification
                - [L9] (p.4) benchmark where each claim is annotated SUPPORTS, REFUTES, or NOT ENOUGH INFO, based
                - [L9] (p.4) on if there exists a Wikipedia passage to verify the claim.
                - [L9] (p.4) In this work, we operate in a question-only
                - [L9] (p.4) setup for both tasks, where models only receive the question/claim as input without access to support
              - [L8] (p.4) paragraphs, and have to rely on their internal knowledge or retrieve knowledge via interacting with
              - [L8] (p.4) an external environment to support reasoning.
              - [L8] (p.4) Action
              - [L8] (p.4) Space
            - [L7] (p.4) We
            - [L7] (p.4) design
            - [L7] (p.4) a
            - [L7] (p.4) simple
            - [L7] (p.4) Wikipedia
            - [L7] (p.4) web
            - [L7] (p.4) API
            - [L7] (p.4) with
            - [L7] (p.4) three
            - [L7] (p.4) types
            - [L7] (p.4) of
            - [L7] (p.4) actions
            - [L7] (p.4) to
            - [L7] (p.4) support
            - [L7] (p.4) interactive information retrieval:
            - [L7] (p.4) (1)
              - **[L8] (p.4) search**
            - [L7] (p.4) [
              - [L8] (p.4) entity
            - [L7] (p.4) ], which returns the first 5 sentences from
            - [L7] (p.4) the corresponding
              - [L8] (p.4) entity
            - [L7] (p.4) wiki page if it exists,
            - [L7] (p.4) or else suggests top-5 similar entities from the
              - [L8] (p.4) Wikipedia search engine, (2)
              - **[L8] (p.4) lookup**
              - [L8] (p.4) [
              - [L8] (p.4) string
              - [L8] (p.4) ], which would return the next sentence in the page
                - [L9] (p.4) containing
              - [L8] (p.4) string
                - [L9] (p.4) , simulating Ctrl+F functionality on the browser.
                - [L9] (p.4) (3)
              - **[L8] (p.4) finish**
                - [L9] (p.4) [
              - [L8] (p.4) answer
                - [L9] (p.4) ], which
                - [L9] (p.4) would finish the current task with
              - [L8] (p.4) answer
                - [L9] (p.4) .
                - [L9] (p.4) We note that this action space mostly can only retrieve a
                - [L9] (p.4) small part of a passage based on exact passage name, which is significantly weaker than state-of-the-
                - [L9] (p.4) art lexical or neural retrievers.
                - [L9] (p.4) The purpose is to simulate how humans would interact with Wikipedia,
              - [L8] (p.4) and force models to retrieve via explicit reasoning in language.
              - [L8] (p.4) 3.2
              - [L8] (p.4) M
                                - [L17] (p.4) ETHODS
              - **[L8] (p.4) ReAct**
              - [L8] (p.4) Prompting
                - [L9] (p.4) For HotpotQA and Fever, we randomly select 6 and 3 cases
                - [L9] (p.4) from the training
              - [L8] (p.4) set and manually compose
              - [L8] (p.4) ReAct
              - [L8] (p.4) -format trajectories to use as few-shot exemplars in the prompts.
                - [L9] (p.4) Similar to Figure 1(d), each trajectory consists of multiple thought-action-observation steps (i.e. dense
                - [L9] (p.4) thought), where free-form thoughts are used for various purposes.
                - [L9] (p.4) Specifically, we use a combination
              - [L8] (p.4) of thoughts that decompose questions (“I need to search x, find y, then find z”), extract information
            - [L7] (p.4) from Wikipedia observations (“x was started in 1844”, “The paragraph does not tell x”), perform
              - [L8] (p.4) commonsense (“x is not y, so z must instead be...”)
              - [L8] (p.4) or arithmetic reasoning (“1844 < 1989”), guide
                        - [L13] (p.4) We find more examples do not improve performance.
              - [L8] (p.4) 4
              - [L8] (p.5) Published as a conference paper at ICLR 2023
                              - [L16] (p.5) Prompt Method
                              - [L16] (p.5) HotpotQA
                              - [L16] (p.5) Fever
                              - [L16] (p.5) (EM)
                              - [L16] (p.5) (Acc)
                              - [L16] (p.5) Standard
                              - [L16] (p.5) 28.7
                              - [L16] (p.5) 57.1
                              - [L16] (p.5) CoT
                              - [L16] (p.5) 29.4
                              - [L16] (p.5) 56.3
                              - [L16] (p.5) CoT-SC
                              - [L16] (p.5) 33.4
                              - [L16] (p.5) 60.4
                              - [L16] (p.5) Act
                              - [L16] (p.5) 25.7
                              - [L16] (p.5) 58.9
                              - [L16] (p.5) ReAct
                              - [L16] (p.5) 27.4
                              - [L16] (p.5) 60.9
                              - [L16] (p.5) CoT-SC
                              - [L16] (p.5) →
                              - [L16] (p.5) ReAct
                              - [L16] (p.5) 34.2
                              - [L16] (p.5) 64.6
                              - [L16] (p.5) ReAct
                              - [L16] (p.5) →
                              - [L16] (p.5) CoT-SC
                              - [L16] (p.5) 35.1
                              - [L16] (p.5) 62.0
                              - [L16] (p.5) Supervised SoTA
                              - [L16] (p.5) 67.5
                              - [L16] (p.5) 89.5
                - [L9] (p.5) Table 1:
                - [L9] (p.5) PaLM-540B prompting results on
              - [L8] (p.5) HotpotQA and Fever.
              - [L8] (p.5) Figure 2:
              - [L8] (p.5) PaLM-540B prompting results with respect to
              - [L8] (p.5) number of
              - [L8] (p.5) CoT-SC
              - [L8] (p.5) samples used.
                - [L9] (p.5) search reformulation (“maybe I can search/look up x instead”), and synthesize the final answer (“...so
              - [L8] (p.5) the answer is x”).
              - [L8] (p.5) See Appendix C for more details.
              - [L8] (p.5) Baselines
                - [L9] (p.5) We systematically ablate
              - [L8] (p.5) ReAct
                - [L9] (p.5) trajectories to build prompts for multiple baselines (with
            - [L7] (p.5) formats as Figure 1(1a-1c)):
            - [L7] (p.5) (a)
              - [L8] (p.5) Standard prompting
            - [L7] (p.5) (
              - [L8] (p.5) Standard
            - [L7] (p.5) ), which removes all thoughts,
            - [L7] (p.5) actions,
            - [L7] (p.5) observations in
              - [L8] (p.5) ReAct
            - [L7] (p.5) trajectories.
            - [L7] (p.5) (b)
              - [L8] (p.5) Chain-of-thought prompting
            - [L7] (p.5) (
              - [L8] (p.5) CoT
            - [L7] (p.5) ) (Wei et al.,
            - [L7] (p.5) 2022),
            - [L7] (p.5) which removes actions and observations and serve as a reasoning-only baseline.
            - [L7] (p.5) We also
              - [L8] (p.5) build a self-consistency baseline (
              - [L8] (p.5) CoT-SC
              - [L8] (p.5) ) (Wang et al., 2022a;b) by sampling 21
              - [L8] (p.5) CoT
              - [L8] (p.5) trajectories
                - [L9] (p.5) with decoding temperature 0.7 during inference and adopting the majority answer, which is found to
                - [L9] (p.5) consistently boost performance over
              - [L8] (p.5) CoT
                - [L9] (p.5) . (c)
              - [L8] (p.5) Acting-only prompt
                - [L9] (p.5) (
              - [L8] (p.5) Act
                - [L9] (p.5) ), which removes thoughts
            - [L7] (p.5) in
              - [L8] (p.5) ReAct
            - [L7] (p.5) trajectories, loosely resembling how WebGPT (Nakano et al., 2021) interacts with the
                - [L9] (p.5) Internet to answer questions, though it operates on a different task and action space, and uses imitation
              - [L8] (p.5) and reinforcement learning instead of prompting.
              - [L8] (p.5) Combining Internal and External Knowledge
              - [L8] (p.5) As will be detail in Section 3.3, we observe that
            - [L7] (p.5) the problem solving process demonstrated by
              - [L8] (p.5) ReAct
            - [L7] (p.5) is more factual and grounded, whereas
              - [L8] (p.5) CoT
            - [L7] (p.5) is
            - [L7] (p.5) more
            - [L7] (p.5) accurate
            - [L7] (p.5) in
            - [L7] (p.5) formulating
            - [L7] (p.5) reasoning
            - [L7] (p.5) structure
            - [L7] (p.5) but
            - [L7] (p.5) can
            - [L7] (p.5) easily
            - [L7] (p.5) suffer
            - [L7] (p.5) from
            - [L7] (p.5) hallucinated
            - [L7] (p.5) facts
            - [L7] (p.5) or thoughts.
            - [L7] (p.5) We therefore propose to incorporate
              - [L8] (p.5) ReAct
            - [L7] (p.5) and
              - [L8] (p.5) CoT-SC
            - [L7] (p.5) , and let the model decide
                - [L9] (p.5) when to switch to the other method based on the following heuristics:
                - [L9] (p.5) A)
              - **[L8] (p.5) ReAct**
              - [L8] (p.5) →
              - **[L8] (p.5) CoT-SC**
                - [L9] (p.5) : when
              - [L8] (p.5) ReAct
            - [L7] (p.5) fails to return an answer within given steps, back off to
              - [L8] (p.5) CoT-SC
            - [L7] (p.5) . We set 7 and 5 steps for
            - [L7] (p.5) HotpotQA and FEVER respectively as we find more steps will not improve
              - [L8] (p.5) ReAct
            - [L7] (p.5) performance
            - [L7] (p.5) .
                - [L9] (p.5) B)
              - **[L8] (p.5) CoT-SC**
              - [L8] (p.5) →
              - **[L8] (p.5) ReAct**
                - [L9] (p.5) :
                - [L9] (p.5) when the majority answer among
              - [L8] (p.5) n
              - [L8] (p.5) CoT-SC
                - [L9] (p.5) samples occurs less than
              - [L8] (p.5) n/
              - [L8] (p.5) 2
              - [L8] (p.5) times (i.e. internal knowledge might not support the task confidently), back off to
              - [L8] (p.5) ReAct
              - [L8] (p.5) .
              - [L8] (p.5) Finetuning
            - [L7] (p.5) Due
            - [L7] (p.5) to
            - [L7] (p.5) the
            - [L7] (p.5) challenge
            - [L7] (p.5) of
            - [L7] (p.5) manually
            - [L7] (p.5) annotating
            - [L7] (p.5) reasoning
            - [L7] (p.5) traces
            - [L7] (p.5) and
            - [L7] (p.5) actions
            - [L7] (p.5) at
            - [L7] (p.5) scale,
            - [L7] (p.5) we
            - [L7] (p.5) consider
            - [L7] (p.5) a
            - [L7] (p.5) bootstraping
            - [L7] (p.5) approach
            - [L7] (p.5) similar
            - [L7] (p.5) to
            - [L7] (p.5) Zelikman
            - [L7] (p.5) et
            - [L7] (p.5) al.
            - [L7] (p.5) (2022),
            - [L7] (p.5) using
            - [L7] (p.5) 3,000
            - [L7] (p.5) trajectories
            - [L7] (p.5) with correct answers generated by
              - [L8] (p.5) ReAct
            - [L7] (p.5) (also for other baselines) to finetune smaller language
            - [L7] (p.5) models (PaLM-8/62B) to decode trajectories (all thoughts,
            - [L7] (p.5) actions,
            - [L7] (p.5) observations) conditioned on
              - [L8] (p.5) input questions/claims.
              - [L8] (p.5) More details are in Appendix B.1.
              - [L8] (p.5) 3.3
              - [L8] (p.5) R
                                - [L17] (p.5) ESULTS
                                - [L17] (p.5) AND
              - [L8] (p.5) O
                                - [L17] (p.5) BSERVATIONS
              - **[L8] (p.5) ReAct**
              - [L8] (p.5) outperforms
              - **[L8] (p.5) Act**
              - [L8] (p.5) consistently
            - [L7] (p.5) Table 1 shows HotpotQA and Fever results using PaLM-
              - [L8] (p.5) 540B as the base model with different prompting methods.
              - [L8] (p.5) We note that
              - [L8] (p.5) ReAct
              - [L8] (p.5) is better than
              - [L8] (p.5) Act
              - [L8] (p.5) on both tasks, demonstrating the value of reasoning to guide acting, especially for synthesizing the
                - [L9] (p.5) final answer, as shown in Figure 1 (1c-d).
                - [L9] (p.5) Fine-tuning results 3 also confirm the benefit of reasoning
              - [L8] (p.5) traces for more informed acting.
                        - [L13] (p.5) Of all trajectories with correct final answers, those with 7 steps on HotpotQA and 5 steps on FEVER only
                        - [L13] (p.5) take up 0.84% and 1.33% respectively.
              - [L8] (p.5) 5
              - [L8] (p.6) Published as a conference paper at ICLR 2023
            - [L7] (p.6) Table
            - [L7] (p.6) 2:
            - [L7] (p.6) Types
            - [L7] (p.6) of
            - [L7] (p.6) success
            - [L7] (p.6) and
            - [L7] (p.6) failure
            - [L7] (p.6) modes
            - [L7] (p.6) of
              - [L8] (p.6) ReAct
            - [L7] (p.6) and
              - [L8] (p.6) CoT
            - [L7] (p.6) on
            - [L7] (p.6) HotpotQA,
            - [L7] (p.6) as
            - [L7] (p.6) well
            - [L7] (p.6) as
            - [L7] (p.6) their
              - [L8] (p.6) percentages in randomly selected examples studied by human.
              - **[L8] (p.6) ReAct**
              - [L8] (p.6) vs.
              - **[L8] (p.6) CoT**
                - [L9] (p.6) On the other hand,
              - [L8] (p.6) ReAct
                - [L9] (p.6) outperforms
              - [L8] (p.6) CoT
                - [L9] (p.6) on Fever (60.9 vs. 56.3) and slightly
              - [L8] (p.6) lags behind
              - [L8] (p.6) CoT
              - [L8] (p.6) on HotpotQA (27.4 vs. 29.4).
              - [L8] (p.6) Fever claims for SUPPORTS/REFUTES might only
                - [L9] (p.6) differ by a slight amount (see Appendix D.1), so acting to retrieve accurate and up-to-date knowledge
              - [L8] (p.6) is vital.
              - [L8] (p.6) To better understand the behavioral difference between
              - [L8] (p.6) ReAct
              - [L8] (p.6) and
              - [L8] (p.6) CoT
              - [L8] (p.6) on HotpotQA, we
              - [L8] (p.6) randomly sampled 50 trajectories with correct and incorrect answers (judged by EM) from
              - [L8] (p.6) ReAct
            - [L7] (p.6) and
              - [L8] (p.6) CoT
            - [L7] (p.6) respectively (thus 200 examples in total), and manually labeled their success and failure
              - [L8] (p.6) modes in Table 2.
              - [L8] (p.6) Some key observations are as follows:
                - [L9] (p.6) A)
              - [L8] (p.6) Hallucination is a serious problem for
              - **[L8] (p.6) CoT**
                - [L9] (p.6) , resulting in much higher false positive rate than
              - [L8] (p.6) ReAct
              - [L8] (p.6) (14% vs.
              - [L8] (p.6) 6%) in success mode, and make up its major failure mode (56%).
              - [L8] (p.6) In contrast, the
            - [L7] (p.6) problem solving trajectory of
              - [L8] (p.6) ReAct
            - [L7] (p.6) is more grounded, fact-driven, and trustworthy, thanks to the
              - [L8] (p.6) access of an external knowledge base.
            - [L7] (p.6) B)
              - [L8] (p.6) While interleaving reasoning, action and observation steps improves
              - **[L8] (p.6) ReAct**
              - [L8] (p.6) ’s grounded-
              - [L8] (p.6) ness and trustworthiness, such a structural constraint also reduces its flexibility in formulating
              - [L8] (p.6) reasoning steps
            - [L7] (p.6) , leading to more reasoning error rate than
              - [L8] (p.6) CoT
            - [L7] (p.6) . we note that there is one frequent
                - [L9] (p.6) error pattern specific to
              - [L8] (p.6) ReAct
                - [L9] (p.6) , in which the model repetitively generates the previous thoughts and
              - [L8] (p.6) actions, and we categorize it as part of “reasoning error” as the model fails to reason about what the
              - [L8] (p.6) proper next action to take and jump out of the loop
              - [L8] (p.6) .
            - [L7] (p.6) C)
              - [L8] (p.6) For
              - **[L8] (p.6) ReAct**
              - [L8] (p.6) ,
              - [L8] (p.6) successfully
              - [L8] (p.6) retrieving
              - [L8] (p.6) informative
              - [L8] (p.6) knowledge
              - [L8] (p.6) via
              - [L8] (p.6) search
              - [L8] (p.6) is
              - [L8] (p.6) critical.
            - [L7] (p.6) Non-
              - [L8] (p.6) informative search, which counts for 23% of the error cases, derails the model reasoning and gives
            - [L7] (p.6) it a hard time to recover and reformulate thoughts.
            - [L7] (p.6) This is perhaps an expected trade-off between
              - [L8] (p.6) factuality and flexibility, which motivates our proposed strategies of combining two methods.
            - [L7] (p.6) We
            - [L7] (p.6) provide
            - [L7] (p.6) examples
            - [L7] (p.6) for
            - [L7] (p.6) each
            - [L7] (p.6) success
            - [L7] (p.6) and
            - [L7] (p.6) failure
            - [L7] (p.6) modes
            - [L7] (p.6) in
            - [L7] (p.6) Appendix
            - [L7] (p.6) E.1.
            - [L7] (p.6) We
            - [L7] (p.6) also
            - [L7] (p.6) find
            - [L7] (p.6) some
              - [L8] (p.6) HotpotQA questions may contain outdated answer labels, see Figure 4 for example.
              - **[L8] (p.6) ReAct**
              - [L8] (p.6) +
              - **[L8] (p.6) CoT**
              - [L8] (p.6) -SC perform best for prompting LLMs
                - [L9] (p.6) Also shown in Table 1, the best prompting
            - [L7] (p.6) method
            - [L7] (p.6) on
            - [L7] (p.6) HotpotQA
            - [L7] (p.6) and
            - [L7] (p.6) Fever
            - [L7] (p.6) are
              - [L8] (p.6) ReAct
              - [L8] (p.6) →
              - [L8] (p.6) CoT-SC
            - [L7] (p.6) and
              - [L8] (p.6) CoT-SC
              - [L8] (p.6) →
              - [L8] (p.6) ReAct
            - [L7] (p.6) respectively.
                - [L9] (p.6) Furthermore, Figure 2 shows how different methods perform with respect to the number of
              - [L8] (p.6) CoT-SC
              - [L8] (p.6) samples used.
              - [L8] (p.6) While two
              - [L8] (p.6) ReAct
              - [L8] (p.6) +
              - [L8] (p.6) CoT-SC
              - [L8] (p.6) methods are advantageous at one task each, they both
            - [L7] (p.6) significantly
            - [L7] (p.6) and
            - [L7] (p.6) consistently
            - [L7] (p.6) outperform
              - [L8] (p.6) CoT-SC
            - [L7] (p.6) across
            - [L7] (p.6) different
            - [L7] (p.6) number
            - [L7] (p.6) of
            - [L7] (p.6) samples,
            - [L7] (p.6) reaching
              - [L8] (p.6) CoT-SC
                - [L9] (p.6) performance with 21 samples using merely 3-5 samples.
                - [L9] (p.6) These results indicate the value of
              - [L8] (p.6) properly combining model internal knowledge and external knowledge for reasoning tasks.
              - **[L8] (p.6) ReAct**
              - [L8] (p.6) performs best for fine-tuning
              - [L8] (p.6) Figure 3 shows the scaling effect of prompting/finetuning
                - [L9] (p.6) four methods (
              - [L8] (p.6) Standard
                - [L9] (p.6) ,
              - [L8] (p.6) CoT
                - [L9] (p.6) ,
              - [L8] (p.6) Act
                - [L9] (p.6) ,
              - [L8] (p.6) ReAct
                - [L9] (p.6) ) on HotpotQA. With PaLM-8/62B, prompting
              - [L8] (p.6) ReAct
            - [L7] (p.6) performs worst among four methods due to the difficulty to learn both reasoning and acting from
              - [L8] (p.6) in-context examples.
              - [L8] (p.6) However, when finetuned with just 3,000 examples,
              - [L8] (p.6) ReAct
              - [L8] (p.6) becomes the best
              - [L8] (p.6) method among the four, with PaLM-8B finetuned
              - [L8] (p.6) ReAct
              - [L8] (p.6) outperforming all PaLM-62B prompting
                - [L9] (p.6) methods, and PaLM-62B finetuned
              - [L8] (p.6) ReAct
                - [L9] (p.6) outperforming all 540B prompting methods.
                - [L9] (p.6) In contrast,
                - [L9] (p.6) finetuning
              - [L8] (p.6) Standard
                - [L9] (p.6) or
              - [L8] (p.6) CoT
                - [L9] (p.6) is significantly worse than finetuning
              - [L8] (p.6) ReAct
                - [L9] (p.6) or
              - [L8] (p.6) Act
                - [L9] (p.6) for both PaLM-
              - [L8] (p.6) 8/62B, as the former essentially teaches models to memorize (potentially halluincated) knowledge
                - [L9] (p.6) facts, and the latter teaches models how to (reason and) act to access information from Wikipedia, a
              - [L8] (p.6) more generalizable skill for knowledge reasoning.
              - [L8] (p.6) As all prompting methods are still significantly
            - [L7] (p.6) far
            - [L7] (p.6) from
            - [L7] (p.6) domain-specific
            - [L7] (p.6) state-of-the-art
            - [L7] (p.6) approaches
            - [L7] (p.6) (Table
            - [L7] (p.6) 1),
            - [L7] (p.6) we
            - [L7] (p.6) believe
            - [L7] (p.6) finetuning
            - [L7] (p.6) with
            - [L7] (p.6) more
              - [L8] (p.6) human-written data might be a better way to unleash the power of
              - [L8] (p.6) ReAct
              - [L8] (p.6) .
                      - [L12] (p.6) We suspect that this could be due to the sub-optimal greedy decoding procedure, and future work using
                        - [L13] (p.6) better decoding (e.g. beam search) might help address this issue.
              - [L8] (p.6) 6
              - [L8] (p.7) Published as a conference paper at ICLR 2023
                - [L9] (p.7) Figure 3: Scaling results for prompting and finetuning on HotPotQA with
              - [L8] (p.7) ReAct
                - [L9] (p.7) (ours) and baselines.
      - [L4] (p.7) 4
      - [L4] (p.7) D
                    - [L11] (p.7) ECISION
      - [L4] (p.7) M
                    - [L11] (p.7) AKING
      - [L4] (p.7) T
                    - [L11] (p.7) ASKS
            - [L7] (p.7) We
            - [L7] (p.7) also
            - [L7] (p.7) test
              - [L8] (p.7) ReAct
            - [L7] (p.7) on
            - [L7] (p.7) two
            - [L7] (p.7) language-based
            - [L7] (p.7) interactive
            - [L7] (p.7) decision-making
            - [L7] (p.7) tasks,
            - [L7] (p.7) ALFWorld
            - [L7] (p.7) and
                - [L9] (p.7) WebShop, both of which feature complex environments that require agents to act over long horizons
              - [L8] (p.7) with sparse rewards, warranting the need for reasoning to act and explore effectively.
              - [L8] (p.7) ALFWorld
                - [L9] (p.7) ALFWorld (Shridhar et al., 2020b) (Figure 1(2)) is a synthetic text-based game designed
            - [L7] (p.7) to
            - [L7] (p.7) align
            - [L7] (p.7) with
            - [L7] (p.7) the
            - [L7] (p.7) embodied
            - [L7] (p.7) ALFRED
            - [L7] (p.7) benchmark
            - [L7] (p.7) (Shridhar
            - [L7] (p.7) et
            - [L7] (p.7) al.,
            - [L7] (p.7) 2020a).
            - [L7] (p.7) It
            - [L7] (p.7) includes
            - [L7] (p.7) 6
            - [L7] (p.7) types
            - [L7] (p.7) of
              - [L8] (p.7) tasks in which an agent needs to achieve a high-level goal (e.g. examine paper under desklamp) by
                - [L9] (p.7) navigating and interacting with a simulated household via text actions (e.g.
                - [L9] (p.7) go to coffeetable 1, take
                - [L9] (p.7) paper 2, use desklamp 1).
                - [L9] (p.7) A task instance can have more than 50 locations and take an expert policy
                - [L9] (p.7) more than 50 steps to solve, thus challenging an agent to plan and track subgoals, as well as explore
              - [L8] (p.7) systematically (e.g. check all desks one by one for desklamp).
              - [L8] (p.7) In particular, one challenge built into
                - [L9] (p.7) ALFWorld is the need to determine likely locations for common household items (e.g. desklamps will
                - [L9] (p.7) likely be on desks, shelfs, or dressers), making this environment a good fit for LLMs to exploit their
            - [L7] (p.7) pretrained commonsense knowledge.
            - [L7] (p.7) To prompt
              - [L8] (p.7) ReAct
            - [L7] (p.7) , we randomly annotate three trajectories
            - [L7] (p.7) from
            - [L7] (p.7) the
            - [L7] (p.7) training
            - [L7] (p.7) set
            - [L7] (p.7) for
            - [L7] (p.7) each
            - [L7] (p.7) task
            - [L7] (p.7) type,
            - [L7] (p.7) where
            - [L7] (p.7) each
            - [L7] (p.7) trajectory
            - [L7] (p.7) includes
            - [L7] (p.7) sparse
            - [L7] (p.7) thoughts
            - [L7] (p.7) that
            - [L7] (p.7) (1)
                - [L9] (p.7) decompose the goal, (2) track subgoal completion, (3) determine the next subgoal, and (4) reason via
                - [L9] (p.7) commonsense where to find an object and what to do with it.
                - [L9] (p.7) We show prompts used for ALFWorld
              - [L8] (p.7) in Appendix C.4.
              - [L8] (p.7) Following
              - [L8] (p.7) Shridhar et al. (2020b), we evaluate on 134 unseen evaluation games
            - [L7] (p.7) in
            - [L7] (p.7) a
            - [L7] (p.7) task-specific
            - [L7] (p.7) setup.
            - [L7] (p.7) For
            - [L7] (p.7) robustness,
            - [L7] (p.7) we
            - [L7] (p.7) construct
            - [L7] (p.7) 6
            - [L7] (p.7) prompts
            - [L7] (p.7) for
            - [L7] (p.7) each
            - [L7] (p.7) task
            - [L7] (p.7) type
            - [L7] (p.7) through
            - [L7] (p.7) each
              - [L8] (p.7) permutation of 2 annotated trajectories from the 3 we annotate.
              - [L8] (p.7) Act
              - [L8] (p.7) prompts are constructed using
            - [L7] (p.7) the same trajectories, but without thoughts — since task instances are randomly chosen from the
                - [L9] (p.7) training set, it favors neither
              - [L8] (p.7) ReAct
                - [L9] (p.7) nor
              - [L8] (p.7) Act
                - [L9] (p.7) and provides a fair and controlled comparison to test the
                - [L9] (p.7) importance of sparse thoughts.
                - [L9] (p.7) For baselines, we use BUTLER (Shridhar et al., 2020b), an imitation
              - [L8] (p.7) learning agent trained on
              - [L8] (p.7) 10
              - [L8] (p.7) expert trajectories for each task type
              - [L8] (p.7) .
              - [L8] (p.7) WebShop
            - [L7] (p.7) Can
              - [L8] (p.7) ReAct
            - [L7] (p.7) also
            - [L7] (p.7) interact
            - [L7] (p.7) with
            - [L7] (p.7) noisy
            - [L7] (p.7) real-world
            - [L7] (p.7) language
            - [L7] (p.7) environments
            - [L7] (p.7) for
            - [L7] (p.7) practical
            - [L7] (p.7) applications?
            - [L7] (p.7) We
            - [L7] (p.7) investigate
            - [L7] (p.7) WebShop
            - [L7] (p.7) (Yao
            - [L7] (p.7) et
            - [L7] (p.7) al.,
            - [L7] (p.7) 2022),
            - [L7] (p.7) a
            - [L7] (p.7) recently
            - [L7] (p.7) proposed
            - [L7] (p.7) online
            - [L7] (p.7) shopping
                - [L9] (p.7) website environment with 1.18M real-world products and 12k human instructions.
                - [L9] (p.7) Unlike ALFWorld,
                - [L9] (p.7) Webshop contains a high variety of structured and unstructured texts (e.g. product titles, descriptions,
            - [L7] (p.7) and options crawled from Amazon), and requires an agent to purchase a product based on a user
            - [L7] (p.7) instruction
            - [L7] (p.7) (e.g. “I
            - [L7] (p.7) am
            - [L7] (p.7) looking
            - [L7] (p.7) for
            - [L7] (p.7) a
            - [L7] (p.7) nightstand
            - [L7] (p.7) with
            - [L7] (p.7) drawers.
            - [L7] (p.7) It
            - [L7] (p.7) should
            - [L7] (p.7) have
            - [L7] (p.7) a
            - [L7] (p.7) nickel
            - [L7] (p.7) finish,
            - [L7] (p.7) and
                - [L9] (p.7) priced lower than $140”) through web interactions (e.g. search “nightstand drawers”, choose buttons
              - [L8] (p.7) such as “color:
              - [L8] (p.7) modern-nickel-white” or “back to search”).
              - [L8] (p.7) This task is evaluated by average score
            - [L7] (p.7) (percentage of desired attributes covered by the chosen product averaged across all episodes) and
                - [L9] (p.7) success rate (percentage of episodes where the chosen product satisfies all requirements) on 500 test
            - [L7] (p.7) instructions.
            - [L7] (p.7) We formulate
              - [L8] (p.7) Act
            - [L7] (p.7) prompts with actions to search,
            - [L7] (p.7) choose product,
            - [L7] (p.7) choose options,
            - [L7] (p.7) and buy, with
              - [L8] (p.7) ReAct
            - [L7] (p.7) prompts additionally reasoning to determine what to explore, when to buy,
            - [L7] (p.7) and what products options are relevant to the instruction.
            - [L7] (p.7) See Table 6 for an example prompt, and
              - [L8] (p.7) Table 10 for model predictions in the Appendix.
              - [L8] (p.7) We compare to an imitation learning (IL) method
                        - [L13] (p.7) Micheli & Fleuret (2021) finetuned a GPT-2 model on 3553 task instances and achieved a much improved
                        - [L13] (p.7) performance than BUTLER, but it is trained on all task types, thus not included as a baseline.
              - [L8] (p.7) 7
              - [L8] (p.8) Published as a conference paper at ICLR 2023
                          - [L14] (p.8) Method
                          - [L14] (p.8) Pick
                          - [L14] (p.8) Clean
                          - [L14] (p.8) Heat
                          - [L14] (p.8) Cool
                          - [L14] (p.8) Look
                          - [L14] (p.8) Pick 2
                          - [L14] (p.8) All
                          - [L14] (p.8) Act
                          - [L14] (p.8) 88
                          - [L14] (p.8) 42
                          - [L14] (p.8) 74
                          - [L14] (p.8) 67
                          - [L14] (p.8) 72
                          - [L14] (p.8) 41
                          - [L14] (p.8) 45
                          - [L14] (p.8) ReAct
                          - [L14] (p.8) 65
                          - [L14] (p.8) 39
                          - [L14] (p.8) 83
                          - [L14] (p.8) 76
                          - [L14] (p.8) 55
                          - [L14] (p.8) 24
                          - [L14] (p.8) 57
                          - [L14] (p.8) ReAct
                          - [L14] (p.8) 92
                          - [L14] (p.8) 58
                          - [L14] (p.8) 96
                          - [L14] (p.8) 86
                          - [L14] (p.8) 78
                          - [L14] (p.8) 41
                          - [L14] (p.8) 71
                          - [L14] (p.8) ReAct-IM
                          - [L14] (p.8) 55
                          - [L14] (p.8) 59
                          - [L14] (p.8) 60
                          - [L14] (p.8) 55
                          - [L14] (p.8) 23
                          - [L14] (p.8) 24
                          - [L14] (p.8) 48
                          - [L14] (p.8) ReAct-IM
                          - [L14] (p.8) 62
                          - [L14] (p.8) 68
                          - [L14] (p.8) 87
                          - [L14] (p.8) 57
                          - [L14] (p.8) 39
                          - [L14] (p.8) 33
                          - [L14] (p.8) 53
                          - [L14] (p.8) BUTLER
                          - [L14] (p.8) 33
                          - [L14] (p.8) 26
                          - [L14] (p.8) 70
                          - [L14] (p.8) 76
                          - [L14] (p.8) 17
                          - [L14] (p.8) 12
                          - [L14] (p.8) 22
                          - [L14] (p.8) BUTLER
                          - [L14] (p.8) 46
                          - [L14] (p.8) 39
                          - [L14] (p.8) 74
                          - [L14] (p.8) 100
                          - [L14] (p.8) 22
                          - [L14] (p.8) 24
                          - [L14] (p.8) 37
            - [L7] (p.8) Table
            - [L7] (p.8) 3:
            - [L7] (p.8) AlfWorld
            - [L7] (p.8) task-specific
            - [L7] (p.8) success
            - [L7] (p.8) rates
            - [L7] (p.8) (%).
            - [L7] (p.8) BUTLER
            - [L7] (p.8) and
            - [L7] (p.8) BUTLER
            - [L7] (p.8) results are from Table 4 of Shridhar et al. (2020b).
            - [L7] (p.8) All
                - [L9] (p.8) methods use greedy decoding, except that BUTLER uses beam search.
                            - [L15] (p.8) Method
                            - [L15] (p.8) Score
                            - [L15] (p.8) SR
                            - [L15] (p.8) Act
                            - [L15] (p.8) 62.3
                            - [L15] (p.8) 30.1
                            - [L15] (p.8) ReAct
                            - [L15] (p.8) 66.6
                            - [L15] (p.8) 40.0
                            - [L15] (p.8) IL
                            - [L15] (p.8) 59.9
                            - [L15] (p.8) 29.1
                            - [L15] (p.8) IL+RL
                            - [L15] (p.8) 62.4
                            - [L15] (p.8) 28.7
                            - [L15] (p.8) Human
                            - [L15] (p.8) 82.1
                            - [L15] (p.8) 59.6
                            - [L15] (p.8) Expert
                - [L9] (p.8) Table 4:
                - [L9] (p.8) Score and suc-
              - [L8] (p.8) cess rate (SR) on Web-
            - [L7] (p.8) shop.
            - [L7] (p.8) IL/IL+RL taken
              - [L8] (p.8) from Yao et al. (2022).
                - [L9] (p.8) trained with 1,012 human annotated trajectories, and a imitation + reinforcement learning (IL + RL)
              - [L8] (p.8) method additionally trained with 10,587 training instructions.
              - [L8] (p.8) Results
              - [L8] (p.8) ReAct
            - [L7] (p.8) outperforms
              - [L8] (p.8) Act
            - [L7] (p.8) on
            - [L7] (p.8) both
            - [L7] (p.8) ALFWorld
            - [L7] (p.8) (Table
            - [L7] (p.8) 3)
            - [L7] (p.8) and
            - [L7] (p.8) Webshop
            - [L7] (p.8) (Table
            - [L7] (p.8) 4).
            - [L7] (p.8) On
                - [L9] (p.8) ALFWorld, the best
              - [L8] (p.8) ReAct
                - [L9] (p.8) trial achieves an average success rate of 71%, significantly outperforming
            - [L7] (p.8) the best
              - [L8] (p.8) Act
            - [L7] (p.8) (45%) and BUTLER (37%) trials.
            - [L7] (p.8) In fact, even the worse
              - [L8] (p.8) ReAct
            - [L7] (p.8) trial (48%) beats
            - [L7] (p.8) the best trial of both methods.
            - [L7] (p.8) Moreover, the advantage of
              - [L8] (p.8) ReAct
            - [L7] (p.8) over
              - [L8] (p.8) Act
            - [L7] (p.8) is consistent across
              - [L8] (p.8) six controlled trials, with relative performance gain ranging from 33% to 90% and averaging 62%.
            - [L7] (p.8) Qualitatively,
            - [L7] (p.8) we
            - [L7] (p.8) saw
            - [L7] (p.8) that,
            - [L7] (p.8) without
            - [L7] (p.8) any
            - [L7] (p.8) thoughts
            - [L7] (p.8) at
            - [L7] (p.8) all,
              - [L8] (p.8) Act
            - [L7] (p.8) fails
            - [L7] (p.8) to
            - [L7] (p.8) correctly
            - [L7] (p.8) decompose
            - [L7] (p.8) goals
            - [L7] (p.8) into smaller subgoals, or loses track of the current state of the environment.
            - [L7] (p.8) Example trajectories
              - [L8] (p.8) comparing
              - [L8] (p.8) ReAct
              - [L8] (p.8) and
              - [L8] (p.8) Act
              - [L8] (p.8) can be found in Appendix D.2.1 and Appendix D.2.2.
              - [L8] (p.8) On Webshop, one-shot
              - [L8] (p.8) Act
              - [L8] (p.8) prompting already performs on par with IL and IL+RL methods.
              - [L8] (p.8) With
                - [L9] (p.8) additional sparse reasoning,
              - [L8] (p.8) ReAct
                - [L9] (p.8) achieves significantly better performance, with an absolute 10%
                - [L9] (p.8) improvement over the previous best success rate.
                - [L9] (p.8) By checking examples, we find that
              - [L8] (p.8) ReAct
                - [L9] (p.8) is more
              - [L8] (p.8) likely to identify instruction-relevant products and options by reasoning to bridge the gap between
            - [L7] (p.8) noisy observations and actions (e.g. “For ‘space-saving ottoman bench for living room’, the item
            - [L7] (p.8) has options ‘39x18x18inch’ and ‘blue’ and seems good to buy.”).
            - [L7] (p.8) However, existing methods are
              - [L8] (p.8) still far from the performance of expert humans (Table 4), who perform significantly more product
              - [L8] (p.8) explorations and query re-formulations that are still challenging for prompting-based methods.
              - [L8] (p.8) On the value of internal reasoning vs.
              - [L8] (p.8) external feedback
              - [L8] (p.8) To our knowledge,
              - [L8] (p.8) ReAct
              - [L8] (p.8) is the first
                - [L9] (p.8) demonstration of combined reasoning and action using an LLM applied to an interactive environment
              - [L8] (p.8) within a closed-loop system.
              - [L8] (p.8) Perhaps the closest prior work is Inner Monologue (IM), from Huang
            - [L7] (p.8) et
            - [L7] (p.8) al.
            - [L7] (p.8) (2022b),
            - [L7] (p.8) in
            - [L7] (p.8) which
            - [L7] (p.8) actions
            - [L7] (p.8) from
            - [L7] (p.8) an
            - [L7] (p.8) embodied
            - [L7] (p.8) agent
            - [L7] (p.8) are
            - [L7] (p.8) motivated
            - [L7] (p.8) by
            - [L7] (p.8) an
            - [L7] (p.8) eponymous
            - [L7] (p.8) “inner
            - [L7] (p.8) monologue”.
              - [L8] (p.8) However, IM’s “inner monologue” is limited to observations of the environment
              - [L8] (p.8) state and what needs to be completed by the agent for the goal to be satisfied.
            - [L7] (p.8) In contrast, the
            - [L7] (p.8) reasoning traces in
              - [L8] (p.8) ReAct
            - [L7] (p.8) for decision making is flexible and sparse, allowing diverse reasoning
              - [L8] (p.8) types (see Section 2) to be induced for different tasks.
              - [L8] (p.8) To demonstrate the differences between
              - [L8] (p.8) ReAct
              - [L8] (p.8) and IM, and to highlight the importance of internal
              - [L8] (p.8) reasoning vs.
              - [L8] (p.8) simple reactions to external feedback, we ran an ablation experiment using a thought
                - [L9] (p.8) pattern composed of IM-like dense external feedback.
                - [L9] (p.8) As can be seen in Table 3,
              - [L8] (p.8) ReAct
                - [L9] (p.8) substantially
            - [L7] (p.8) outperforms
            - [L7] (p.8) IM-style
            - [L7] (p.8) prompting
            - [L7] (p.8) (
              - [L8] (p.8) ReAct-IM
            - [L7] (p.8) )
            - [L7] (p.8) (71
            - [L7] (p.8) vs. 53
            - [L7] (p.8) overall
            - [L7] (p.8) success
            - [L7] (p.8) rate),
            - [L7] (p.8) with
            - [L7] (p.8) consistent
                - [L9] (p.8) advantages on five out of six tasks.
                - [L9] (p.8) Qualitatively, we observed that
              - [L8] (p.8) ReAct-IM
                - [L9] (p.8) often made mistakes
                - [L9] (p.8) in identifying when subgoals were finished, or what the next subgoal should be, due to a lack of high-
                - [L9] (p.8) level goal decomposition.
                - [L9] (p.8) Additionally, many
              - [L8] (p.8) ReAct-IM
                - [L9] (p.8) trajectories struggled to determine where
                - [L9] (p.8) an item would likely be within the ALFWorld environment, due to a lack of commonsense reasoning.
              - [L8] (p.8) Both shortcomings can be addressed in the
              - [L8] (p.8) ReAct
              - [L8] (p.8) paradigm.
              - [L8] (p.8) More details about
              - [L8] (p.8) ReAct-IM
              - [L8] (p.8) is in
              - [L8] (p.8) Appendix B.2.
              - [L8] (p.8) An example prompt for
              - [L8] (p.8) ReAct-IM
              - [L8] (p.8) can be found in Appendix C.4, and an example
              - [L8] (p.8) trajectory in Appendix D.2.3.
              - [L8] (p.8) 8
              - [L8] (p.9) Published as a conference paper at ICLR 2023
      - [L4] (p.9) 5
      - [L4] (p.9) R
                    - [L11] (p.9) ELATED
      - [L4] (p.9) W
                    - [L11] (p.9) ORK
              - [L8] (p.9) Language model for reasoning
                - [L9] (p.9) Perhaps the most well-known work of using LLMs for reasoning
              - [L8] (p.9) is Chain-of-Thought (CoT) (Wei et al., 2022), which reveals the ability of LLMs to formulate their
                - [L9] (p.9) own “thinking procedure” for problem solving.
                - [L9] (p.9) Several follow-up works have since been performed,
            - [L7] (p.9) including
            - [L7] (p.9) least-to-most
            - [L7] (p.9) prompting
            - [L7] (p.9) for
            - [L7] (p.9) solving
            - [L7] (p.9) complicated
            - [L7] (p.9) tasks
            - [L7] (p.9) (Zhou
            - [L7] (p.9) et
            - [L7] (p.9) al.,
            - [L7] (p.9) 2022),
            - [L7] (p.9) zero-shot-
            - [L7] (p.9) CoT
            - [L7] (p.9) (Kojima
            - [L7] (p.9) et
            - [L7] (p.9) al.,
            - [L7] (p.9) 2022),
            - [L7] (p.9) and
            - [L7] (p.9) reasoning
            - [L7] (p.9) with
            - [L7] (p.9) self-consistency
            - [L7] (p.9) (Wang
            - [L7] (p.9) et
            - [L7] (p.9) al.,
            - [L7] (p.9) 2022a).
            - [L7] (p.9) Recently,
              - [L8] (p.9) (Madaan & Yazdanbakhsh, 2022) systematically studied the formulation and structure of CoT, and
                - [L9] (p.9) observed that the presence of symbols, patterns and texts is crucial to the effectiveness of CoT. Other
                - [L9] (p.9) work has also been extended to more sophisticated reasoning architecture beyond simple prompting.
                - [L9] (p.9) For example Selection-Inference (Creswell et al., 2022) divides the reasoning process into two steps
            - [L7] (p.9) of “selection” and “inference”.
            - [L7] (p.9) STaR (Zelikman et al., 2022) bootstraps the reasoning process by
                - [L9] (p.9) finetuning the model on correct rationales generated by the model itself.
                - [L9] (p.9) Faithful reasoning (Creswell
                - [L9] (p.9) & Shanahan, 2022) decomposes multi-step reasoning into three steps, each performed by a dedicated
            - [L7] (p.9) LM respectively.
            - [L7] (p.9) Similar approaches like Scratchpad (Nye et al., 2021), which finetunes a LM on
                - [L9] (p.9) intermediate computation steps, also demonstrate improvement on multi-step computation problems.
                - [L9] (p.9) In contrast to these methods,
              - [L8] (p.9) ReAct
                - [L9] (p.9) performs more than just isolated, fixed reasoning, and integrates
                - [L9] (p.9) model actions and their corresponding observations into a coherent stream of inputs for the model to
              - [L8] (p.9) reason more accurately and tackle tasks beyond reasoning (e.g. interactive decision making).
              - [L8] (p.9) Language model for decision making
                - [L9] (p.9) The strong capability of LLMs has enabled them to perform
              - [L8] (p.9) tasks beyond language generation, and it is becoming more popular to take advantage of LLMs as a
              - [L8] (p.9) policy model for decision making, especially in interactive environments.
              - [L8] (p.9) WebGPT (Nakano et al.,
              - [L8] (p.9) 2021) uses an LM to interact with web browsers, navigate through web pages, and infer answers to
            - [L7] (p.9) complicated questions from ELI5 (Fan et al., 2019).
            - [L7] (p.9) In comparison to
              - [L8] (p.9) ReAct
            - [L7] (p.9) , WebGPT does not
                - [L9] (p.9) explicitly model the thinking and reasoning procedure, instead rely on expensive human feedback for
              - [L8] (p.9) reinforcement learning.
              - [L8] (p.9) In conversation modeling, chatbots like BlenderBot (Shuster et al., 2022b)
                - [L9] (p.9) and Sparrow (Glaese et al., 2022) and task-oriented dialogue systems like SimpleTOD (Hosseini-Asl
              - [L8] (p.9) et al., 2020) also train LMs to make decision about API calls.
              - [L8] (p.9) Unlike
              - [L8] (p.9) ReAct
              - [L8] (p.9) , they do not explicitly
              - [L8] (p.9) consider the reasoning procedure either, and also relies on expensive datasets and human feedback
              - [L8] (p.9) collections for policy learning.
              - [L8] (p.9) In contrast,
              - [L8] (p.9) ReAct
              - [L8] (p.9) learns a policy in a much cheaper way, since the
              - [L8] (p.9) decision making process only requires language description of the reasoning procedure.
                - [L9] (p.9) LLMS have also been increasingly employed in interactive and embodied environments for planning
              - [L8] (p.9) and decision making.
              - [L8] (p.9) Perhaps most relevant to
              - [L8] (p.9) ReAct
              - [L8] (p.9) in this respect are SayCan (Ahn et al., 2022)
                - [L9] (p.9) and Inner Monologue (Huang et al., 2022b), which use LLMs for robotic action planning and decision
                - [L9] (p.9) making.
                - [L9] (p.9) In SayCan, LLMs were prompted to directly predict possible actions a robot can take, which
            - [L7] (p.9) is then reranked by an affordance model grounded on the visual environments for final prediction.
                - [L9] (p.9) Inner Monologue made further improvements by adding the eponymous “inner monologue", which is
                - [L9] (p.9) implemented as injected feedback from the environment.
                - [L9] (p.9) To our knowledge, Inner Monologue is the
                - [L9] (p.9) first work that demonstrates such a closed-loop system, which
              - [L8] (p.9) ReAct
                - [L9] (p.9) builds on.
                - [L9] (p.9) However, we argue
                - [L9] (p.9) that Inner Monologue does not truly comprise of inner thoughts — this is elaborated in Section 4.
                - [L9] (p.9) We
              - [L8] (p.9) also note that leveraging language as semantically-rich inputs in the process of interactive decision
            - [L7] (p.9) making has been shown to be successful under other settings (Abramson et al., 2020; Karamcheti
              - [L8] (p.9) et al., 2021; Huang et al., 2022a; Li et al., 2022).
              - [L8] (p.9) It is becoming more evident that with the help of
            - [L7] (p.9) LLMs, language as a fundamental cognitive mechanism will play a critical role in interaction and
                - [L9] (p.9) decision making.
                - [L9] (p.9) What is more, progress in LLMs has also inspired the development of versatile and
              - [L8] (p.9) generalist agents like Reed et al. (2022).
      - [L4] (p.9) 6
      - [L4] (p.9) C
                    - [L11] (p.9) ONCLUSION
            - [L7] (p.9) We have proposed
              - [L8] (p.9) ReAct
            - [L7] (p.9) – a simple yet effective method for synergizing reasoning and acting in
                - [L9] (p.9) large language models.
                - [L9] (p.9) Through a diverse set of experiments on multi-hop question-answering, fact
                - [L9] (p.9) checking, and interactive decision-making tasks, we show that
              - [L8] (p.9) ReAct
                - [L9] (p.9) leads to superior performance
            - [L7] (p.9) with interpretable decision traces.
            - [L7] (p.9) Despite the simplicity of our method, complex tasks with large
              - [L8] (p.9) action spaces require more demonstrations to learn well, which unfortunately can easily go beyond
            - [L7] (p.9) the
            - [L7] (p.9) input
            - [L7] (p.9) length
            - [L7] (p.9) limit
            - [L7] (p.9) of
            - [L7] (p.9) in-context
            - [L7] (p.9) learning.
            - [L7] (p.9) We
            - [L7] (p.9) explore
            - [L7] (p.9) the
            - [L7] (p.9) fine-tuning
            - [L7] (p.9) approach
            - [L7] (p.9) on
            - [L7] (p.9) HotpotQA
                        - [L13] (p.9) Human feedback can also be incorporated in a complementary manner but we leave it for future work.
              - [L8] (p.9) 9
              - [L8] (p.10) Published as a conference paper at ICLR 2023
            - [L7] (p.10) with initial promising results, but learning from more high-quality human annotations will be the
            - [L7] (p.10) desiderata
            - [L7] (p.10) to
            - [L7] (p.10) further
            - [L7] (p.10) improve
            - [L7] (p.10) the
            - [L7] (p.10) performance.
            - [L7] (p.10) Scaling
            - [L7] (p.10) up
              - [L8] (p.10) ReAct
            - [L7] (p.10) with
            - [L7] (p.10) multi-task
            - [L7] (p.10) training
            - [L7] (p.10) and
            - [L7] (p.10) combining it with complementary paradigms like reinforcement learning could result in stronger
              - [L8] (p.10) agents that further unlock the potential of LLMs for more applications.
              - [L8] (p.10) A
                                - [L17] (p.10) CKNOWLEDGMENTS
            - [L7] (p.10) We thank the support and feedback of many people from Google Brain team and Princeton NLP
            - [L7] (p.10) Group.
            - [L7] (p.10) This
            - [L7] (p.10) work
            - [L7] (p.10) was
            - [L7] (p.10) supported
            - [L7] (p.10) in
            - [L7] (p.10) part
            - [L7] (p.10) by
            - [L7] (p.10) the
            - [L7] (p.10) National
            - [L7] (p.10) Science
            - [L7] (p.10) Foundation
            - [L7] (p.10) under
            - [L7] (p.10) Grant
            - [L7] (p.10) No.
                - [L9] (p.10) 2107048.
                - [L9] (p.10) Any opinions, findings, and conclusions or recommendations expressed in this material are
              - [L8] (p.10) those of the author(s) and do not necessarily reflect the views of the National Science Foundation.
              - [L8] (p.10) R
                                - [L17] (p.10) EPRODUCIBILITY
              - [L8] (p.10) S
                                - [L17] (p.10) TATEMENT
                - [L9] (p.10) Our main experiments are done on PaLM (Chowdhery et al., 2022), which is not an openly accessible
                - [L9] (p.10) model yet.
                - [L9] (p.10) To increase reproducibility, we have included all used prompts in Appendix C, additional
            - [L7] (p.10) experiments
            - [L7] (p.10) using
            - [L7] (p.10) GPT-3
            - [L7] (p.10) (Brown
            - [L7] (p.10) et
            - [L7] (p.10) al.,
            - [L7] (p.10) 2020)
            - [L7] (p.10) in
            - [L7] (p.10) Appendix
            - [L7] (p.10) A.1,
            - [L7] (p.10) and
            - [L7] (p.10) associated
            - [L7] (p.10) GPT-3
              - [L8] (p.10) ReAct
              - [L8] (p.10) prompting code at
              - [L8] (p.10) https://anonymous.4open.science/r/ReAct-2268/
              - [L8] (p.10) .
              - [L8] (p.10) E
                                - [L17] (p.10) THICS
              - [L8] (p.10) S
                                - [L17] (p.10) TATEMENT
              - [L8] (p.10) ReAct
            - [L7] (p.10) prompts
            - [L7] (p.10) large
            - [L7] (p.10) language
            - [L7] (p.10) models
            - [L7] (p.10) to
            - [L7] (p.10) generate
            - [L7] (p.10) more
            - [L7] (p.10) human
            - [L7] (p.10) interpretable,
            - [L7] (p.10) diagnosable,
            - [L7] (p.10) and
              - [L8] (p.10) controllable task-solving trajectories than previous methods.
              - [L8] (p.10) However, hooking up a large language
            - [L7] (p.10) model with an action space to interact with external environments (e.g. the web, physical environ-
                - [L9] (p.10) ments) has potential dangers, e.g.
                - [L9] (p.10) looking up inappropriate or private information, or taking harmful
            - [L7] (p.10) actions
            - [L7] (p.10) in
            - [L7] (p.10) an
            - [L7] (p.10) environment.
            - [L7] (p.10) Our
            - [L7] (p.10) experiments
            - [L7] (p.10) minimize
            - [L7] (p.10) such
            - [L7] (p.10) risks
            - [L7] (p.10) by
            - [L7] (p.10) limiting
            - [L7] (p.10) the
            - [L7] (p.10) interactions
            - [L7] (p.10) to
                - [L9] (p.10) specific websites (Wikipedia or WebShop) that are free of private information, without any dangerous
              - [L8] (p.10) actions in the action space design (i.e. models cannot really buy products on WebShop the research
                - [L9] (p.10) benchmark, or edit Wikipedia).
                - [L9] (p.10) We believe researchers should be aware of such risks before designing
              - [L8] (p.10) more extensive experiments in the future.
      - [L4] (p.10) R
                    - [L11] (p.10) EFERENCES
              - [L8] (p.10) Josh Abramson, Arun Ahuja, Iain Barr, Arthur Brussee, Federico Carnevale, Mary Cassin, Rachita
            - [L7] (p.10) Chhaparia, Stephen Clark, Bogdan Damoc, Andrew Dudzik, Petko Georgiev, Aurelia Guy, Tim
                - [L9] (p.10) Harley, Felix Hill, Alden Hung, Zachary Kenton, Jessica Landon, Timothy Lillicrap, Kory Mathew-
                - [L9] (p.10) son, Soˇna Mokrá, Alistair Muldal, Adam Santoro, Nikolay Savinov, Vikrant Varma, Greg Wayne,
            - [L7] (p.10) Duncan Williams, Nathaniel Wong, Chen Yan, and Rui Zhu.
            - [L7] (p.10) Imitating interactive intelligence,
              - [L8] (p.10) 2020.
              - [L8] (p.10) URL
              - [L8] (p.10) https://arxiv.org/abs/2012.05672
              - [L8] (p.10) .
                - [L9] (p.10) Michael Ahn, Anthony Brohan, Noah Brown, Yevgen Chebotar, Omar Cortes, Byron David, Chelsea
                - [L9] (p.10) Finn, Chuyuan Fu, Keerthana Gopalakrishnan, Karol Hausman, Alex Herzog, Daniel Ho, Jasmine
                - [L9] (p.10) Hsu, Julian Ibarz, Brian Ichter, Alex Irpan, Eric Jang, Rosario Jauregui Ruano, Kyle Jeffrey, Sally
            - [L7] (p.10) Jesmonth,
            - [L7] (p.10) Nikhil
            - [L7] (p.10) J
            - [L7] (p.10) Joshi,
            - [L7] (p.10) Ryan
            - [L7] (p.10) Julian,
            - [L7] (p.10) Dmitry
            - [L7] (p.10) Kalashnikov,
            - [L7] (p.10) Yuheng
            - [L7] (p.10) Kuang,
            - [L7] (p.10) Kuang-Huei
            - [L7] (p.10) Lee,
            - [L7] (p.10) Sergey Levine, Yao Lu, Linda Luu, Carolina Parada, Peter Pastor, Jornell Quiambao, Kanishka
                - [L9] (p.10) Rao, Jarek Rettinghouse, Diego Reyes, Pierre Sermanet, Nicolas Sievers, Clayton Tan, Alexander
            - [L7] (p.10) Toshev,
            - [L7] (p.10) Vincent
            - [L7] (p.10) Vanhoucke,
            - [L7] (p.10) Fei
            - [L7] (p.10) Xia,
            - [L7] (p.10) Ted
            - [L7] (p.10) Xiao,
            - [L7] (p.10) Peng
            - [L7] (p.10) Xu,
            - [L7] (p.10) Sichun
            - [L7] (p.10) Xu,
            - [L7] (p.10) Mengyuan
            - [L7] (p.10) Yan,
            - [L7] (p.10) and
            - [L7] (p.10) Andy Zeng.
            - [L7] (p.10) Do as i can, not as i say:
            - [L7] (p.10) Grounding language in robotic affordances, 2022.
            - [L7] (p.10) URL
              - [L8] (p.10) https://arxiv.org/abs/2204.01691
              - [L8] (p.10) .
            - [L7] (p.10) Ben
            - [L7] (p.10) Alderson-Day
            - [L7] (p.10) and
            - [L7] (p.10) Charles
            - [L7] (p.10) Fernyhough.
            - [L7] (p.10) Inner
            - [L7] (p.10) speech:
            - [L7] (p.10) development,
            - [L7] (p.10) cognitive
            - [L7] (p.10) functions,
              - [L8] (p.10) phenomenology, and neurobiology.
              - [L8] (p.10) Psychological bulletin
              - [L8] (p.10) , 141(5):931, 2015.
              - [L8] (p.10) Alan Baddeley.
              - [L8] (p.10) Working memory.
              - [L8] (p.10) Science
              - [L8] (p.10) , 255(5044):556–559, 1992.
            - [L7] (p.10) Tom Brown, Benjamin Mann, Nick Ryder, Melanie Subbiah, Jared D Kaplan, Prafulla Dhariwal,
            - [L7] (p.10) Arvind Neelakantan, Pranav Shyam, Girish Sastry, Amanda Askell, et al.
            - [L7] (p.10) Language models are
              - [L8] (p.10) few-shot learners.
              - [L8] (p.10) Advances in neural information processing systems
              - [L8] (p.10) , 33:1877–1901, 2020.
              - [L8] (p.10) 10
              - [L8] (p.11) Published as a conference paper at ICLR 2023
            - [L7] (p.11) Aakanksha
            - [L7] (p.11) Chowdhery,
            - [L7] (p.11) Sharan
            - [L7] (p.11) Narang,
            - [L7] (p.11) Jacob
            - [L7] (p.11) Devlin,
            - [L7] (p.11) Maarten
            - [L7] (p.11) Bosma,
            - [L7] (p.11) Gaurav
            - [L7] (p.11) Mishra,
            - [L7] (p.11) Adam
            - [L7] (p.11) Roberts,
            - [L7] (p.11) Paul Barham,
            - [L7] (p.11) Hyung Won Chung,
            - [L7] (p.11) Charles Sutton,
            - [L7] (p.11) Sebastian Gehrmann,
            - [L7] (p.11) et al.
            - [L7] (p.11) Palm:
              - [L8] (p.11) Scaling language modeling with pathways.
              - [L8] (p.11) arXiv preprint arXiv:2204.02311
              - [L8] (p.11) , 2022.
                - [L9] (p.11) Antonia Creswell and Murray Shanahan.
                - [L9] (p.11) Faithful reasoning using large language models, 2022.
                - [L9] (p.11) URL
              - [L8] (p.11) https://arxiv.org/abs/2208.14271
              - [L8] (p.11) .
            - [L7] (p.11) Antonia
            - [L7] (p.11) Creswell,
            - [L7] (p.11) Murray
            - [L7] (p.11) Shanahan,
            - [L7] (p.11) and
            - [L7] (p.11) Irina
            - [L7] (p.11) Higgins.
            - [L7] (p.11) Selection-inference:
            - [L7] (p.11) Exploiting
            - [L7] (p.11) large
                - [L9] (p.11) language models for interpretable logical reasoning, 2022.
                - [L9] (p.11) URL
              - [L8] (p.11) https://arxiv.org/abs/
              - [L8] (p.11) 2205.09712
              - [L8] (p.11) .
            - [L7] (p.11) Angela Fan, Yacine Jernite, Ethan Perez, David Grangier, Jason Weston, and Michael Auli.
            - [L7] (p.11) ELI5:
            - [L7] (p.11) Long form question answering.
            - [L7] (p.11) In
            - [L7] (p.11) Proceedings of the 57th Annual Meeting of the Association
              - [L8] (p.11) for Computational Linguistics
              - [L8] (p.11) , pp. 3558–3567, Florence, Italy, July 2019. Association for Com-
            - [L7] (p.11) putational Linguistics.
            - [L7] (p.11) doi:
            - [L7] (p.11) 10.18653/v1/P19-1346.
            - [L7] (p.11) URL
              - [L8] (p.11) https://aclanthology.org/
              - [L8] (p.11) P19-1346
              - [L8] (p.11) .
            - [L7] (p.11) Charles
            - [L7] (p.11) Fernyhough.
            - [L7] (p.11) Vygotsky,
            - [L7] (p.11) luria,
            - [L7] (p.11) and
            - [L7] (p.11) the
            - [L7] (p.11) social
            - [L7] (p.11) brain.
            - [L7] (p.11) Self
            - [L7] (p.11) and
            - [L7] (p.11) social
            - [L7] (p.11) regulation:
            - [L7] (p.11) Social
                - [L9] (p.11) interaction and the development of social understanding and executive functions
                - [L9] (p.11) , pp. 56–79, 2010.
            - [L7] (p.11) Amelia
            - [L7] (p.11) Glaese,
            - [L7] (p.11) Nat
            - [L7] (p.11) McAleese,
            - [L7] (p.11) Maja
            - [L7] (p.11) Trebacz,
            - [L7] (p.11) John
            - [L7] (p.11) Aslanides,
            - [L7] (p.11) Vlad
            - [L7] (p.11) Firoiu,
            - [L7] (p.11) Timo
            - [L7] (p.11) Ewalds,
            - [L7] (p.11) Mari-
            - [L7] (p.11) beth
            - [L7] (p.11) Rauh,
            - [L7] (p.11) Laura
            - [L7] (p.11) Weidinger,
            - [L7] (p.11) Martin
            - [L7] (p.11) Chadwick,
            - [L7] (p.11) Phoebe
            - [L7] (p.11) Thacker,
            - [L7] (p.11) Lucy
            - [L7] (p.11) Campbell-Gillingham,
            - [L7] (p.11) Jonathan
            - [L7] (p.11) Uesato,
            - [L7] (p.11) Po-Sen
            - [L7] (p.11) Huang,
            - [L7] (p.11) Ramona
            - [L7] (p.11) Comanescu,
            - [L7] (p.11) Fan
            - [L7] (p.11) Yang,
            - [L7] (p.11) Abigail
            - [L7] (p.11) See,
            - [L7] (p.11) Sumanth
            - [L7] (p.11) Dathathri,
            - [L7] (p.11) Rory
            - [L7] (p.11) Greig,
            - [L7] (p.11) Charlie
            - [L7] (p.11) Chen,
            - [L7] (p.11) Doug
            - [L7] (p.11) Fritz,
            - [L7] (p.11) Jaume
            - [L7] (p.11) Sanchez
            - [L7] (p.11) Elias,
            - [L7] (p.11) Richard
            - [L7] (p.11) Green,
            - [L7] (p.11) Soˇna
            - [L7] (p.11) Mokrá,
            - [L7] (p.11) Nicholas
            - [L7] (p.11) Fernando,
            - [L7] (p.11) Boxi
            - [L7] (p.11) Wu,
            - [L7] (p.11) Rachel
            - [L7] (p.11) Foley,
            - [L7] (p.11) Susannah
            - [L7] (p.11) Young,
            - [L7] (p.11) Iason
            - [L7] (p.11) Gabriel,
            - [L7] (p.11) William
            - [L7] (p.11) Isaac,
            - [L7] (p.11) John
            - [L7] (p.11) Mellor,
            - [L7] (p.11) Demis
            - [L7] (p.11) Hassabis,
            - [L7] (p.11) Koray
            - [L7] (p.11) Kavukcuoglu,
            - [L7] (p.11) Lisa
            - [L7] (p.11) Anne
            - [L7] (p.11) Hendricks,
            - [L7] (p.11) and
            - [L7] (p.11) Geoffrey
            - [L7] (p.11) Irving.
            - [L7] (p.11) Improving
            - [L7] (p.11) alignment
            - [L7] (p.11) of
            - [L7] (p.11) dialogue
            - [L7] (p.11) agents
            - [L7] (p.11) via
            - [L7] (p.11) targeted
            - [L7] (p.11) human
            - [L7] (p.11) judgements,
            - [L7] (p.11) 2022.
            - [L7] (p.11) URL
              - [L8] (p.11) https://storage.googleapis.com/deepmind-media/DeepMind.
              - [L8] (p.11) com/Authors-Notes/sparrow/sparrow-final.pdf
              - [L8] (p.11) .
                - [L9] (p.11) Ehsan Hosseini-Asl, Bryan McCann, Chien-Sheng Wu, Semih Yavuz, and Richard Socher.
                - [L9] (p.11) A simple
              - [L8] (p.11) language model for task-oriented dialogue.
              - [L8] (p.11) Advances in Neural Information Processing Systems
              - [L8] (p.11) ,
              - [L8] (p.11) 33:20179–20191, 2020.
              - [L8] (p.11) Wenlong Huang, Pieter Abbeel, Deepak Pathak, and Igor Mordatch.
              - [L8] (p.11) Language models as zero-shot
                - [L9] (p.11) planners:
                - [L9] (p.11) Extracting actionable knowledge for embodied agents.
                - [L9] (p.11) arXiv preprint arXiv:2201.07207
                - [L9] (p.11) ,
              - [L8] (p.11) 2022a.
                - [L9] (p.11) Wenlong Huang, Fei Xia, Ted Xiao, Harris Chan, Jacky Liang, Pete Florence, Andy Zeng, Jonathan
                - [L9] (p.11) Tompson, Igor Mordatch, Yevgen Chebotar, et al.
                - [L9] (p.11) Inner monologue:
                - [L9] (p.11) Embodied reasoning through
              - [L8] (p.11) planning with language models.
              - [L8] (p.11) arXiv preprint arXiv:2207.05608
              - [L8] (p.11) , 2022b.
                - [L9] (p.11) Siddharth Karamcheti, Megha Srivastava, Percy Liang, and Dorsa Sadigh.
                - [L9] (p.11) Lila:
                - [L9] (p.11) Language-informed
                - [L9] (p.11) latent actions.
                - [L9] (p.11) In
                - [L9] (p.11) CoRL
                - [L9] (p.11) , pp. 1379–1390, 2021.
                - [L9] (p.11) URL
              - [L8] (p.11) https://proceedings.mlr.press/
              - [L8] (p.11) v164/karamcheti22a.html
              - [L8] (p.11) .
            - [L7] (p.11) Takeshi Kojima, Shixiang Shane Gu, Machel Reid, Yutaka Matsuo, and Yusuke Iwasawa.
            - [L7] (p.11) Large
              - [L8] (p.11) language models are zero-shot reasoners.
              - [L8] (p.11) arXiv preprint arXiv:2205.11916
              - [L8] (p.11) , 2022.
            - [L7] (p.11) Angeliki
            - [L7] (p.11) Lazaridou,
            - [L7] (p.11) Elena
            - [L7] (p.11) Gribovskaya,
            - [L7] (p.11) Wojciech
            - [L7] (p.11) Stokowiec,
            - [L7] (p.11) and
            - [L7] (p.11) Nikolai
            - [L7] (p.11) Grigorev.
            - [L7] (p.11) Internet-
            - [L7] (p.11) augmented language models through few-shot prompting for open-domain question answering.
              - [L8] (p.11) arXiv preprint arXiv:2203.05115
              - [L8] (p.11) , 2022.
              - [L8] (p.11) Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal,
                - [L9] (p.11) Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, et al.
                - [L9] (p.11) Retrieval-augmented genera-
              - [L8] (p.11) tion for knowledge-intensive nlp tasks.
              - [L8] (p.11) Advances in Neural Information Processing Systems
              - [L8] (p.11) , 33:
              - [L8] (p.11) 9459–9474, 2020.
            - [L7] (p.11) Shuang
            - [L7] (p.11) Li,
            - [L7] (p.11) Xavier
            - [L7] (p.11) Puig,
            - [L7] (p.11) Chris
            - [L7] (p.11) Paxton,
            - [L7] (p.11) Yilun
            - [L7] (p.11) Du,
            - [L7] (p.11) Clinton
            - [L7] (p.11) Wang,
            - [L7] (p.11) Linxi
            - [L7] (p.11) Fan,
            - [L7] (p.11) Tao
            - [L7] (p.11) Chen,
            - [L7] (p.11) De-An
            - [L7] (p.11) Huang, Ekin Akyürek, Anima Anandkumar, Jacob Andreas, Igor Mordatch, Antonio Torralba,
                - [L9] (p.11) and Yuke Zhu.
                - [L9] (p.11) Pre-trained language models for interactive decision-making, 2022.
                - [L9] (p.11) URL
              - [L8] (p.11) https:
              - [L8] (p.11) //arxiv.org/abs/2202.01771
              - [L8] (p.11) .
              - [L8] (p.11) 11
              - [L8] (p.12) Published as a conference paper at ICLR 2023
              - [L8] (p.12) Aleksandr Romanovich Luria.
              - [L8] (p.12) Ls vygotsky and the problem of localization of functions.
              - [L8] (p.12) Neuropsy-
              - [L8] (p.12) chologia
              - [L8] (p.12) , 3(4):387–392, 1965.
              - [L8] (p.12) Aman Madaan and Amir Yazdanbakhsh.
              - [L8] (p.12) Text and patterns:
              - [L8] (p.12) For effective chain of thought, it takes
              - [L8] (p.12) two to tango, 2022.
              - [L8] (p.12) URL
              - [L8] (p.12) https://arxiv.org/abs/2209.07686
              - [L8] (p.12) .
            - [L7] (p.12) Vincent
            - [L7] (p.12) Micheli
            - [L7] (p.12) and
            - [L7] (p.12) François
            - [L7] (p.12) Fleuret.
            - [L7] (p.12) Language
            - [L7] (p.12) models
            - [L7] (p.12) are
            - [L7] (p.12) few-shot
            - [L7] (p.12) butlers.
            - [L7] (p.12) arXiv
            - [L7] (p.12) preprint
              - [L8] (p.12) arXiv:2104.07972
              - [L8] (p.12) , 2021.
              - [L8] (p.12) Reiichiro Nakano, Jacob Hilton, Suchir Balaji, Jeff Wu, Long Ouyang, Christina Kim, Christopher
                - [L9] (p.12) Hesse, Shantanu Jain, Vineet Kosaraju, William Saunders, Xu Jiang, Karl Cobbe, Tyna Eloundou,
                - [L9] (p.12) Gretchen Krueger, Kevin Button, Matthew Knight, Benjamin Chess, and John Schulman.
                - [L9] (p.12) Webgpt:
            - [L7] (p.12) Browser-assisted
            - [L7] (p.12) question-answering
            - [L7] (p.12) with
            - [L7] (p.12) human
            - [L7] (p.12) feedback,
            - [L7] (p.12) 2021.
            - [L7] (p.12) URL
              - [L8] (p.12) https://arxiv.
              - [L8] (p.12) org/abs/2112.09332
              - [L8] (p.12) .
              - [L8] (p.12) Maxwell Nye, Anders Johan Andreassen, Guy Gur-Ari, Henryk Michalewski, Jacob Austin, David
            - [L7] (p.12) Bieber,
            - [L7] (p.12) David
            - [L7] (p.12) Dohan,
            - [L7] (p.12) Aitor
            - [L7] (p.12) Lewkowycz,
            - [L7] (p.12) Maarten
            - [L7] (p.12) Bosma,
            - [L7] (p.12) David
            - [L7] (p.12) Luan,
            - [L7] (p.12) Charles
            - [L7] (p.12) Sutton,
            - [L7] (p.12) and
            - [L7] (p.12) Augustus
            - [L7] (p.12) Odena.
            - [L7] (p.12) Show
            - [L7] (p.12) your
            - [L7] (p.12) work:
            - [L7] (p.12) Scratchpads
            - [L7] (p.12) for
            - [L7] (p.12) intermediate
            - [L7] (p.12) computation
            - [L7] (p.12) with
            - [L7] (p.12) language
              - [L8] (p.12) models, 2021.
              - [L8] (p.12) URL
              - [L8] (p.12) https://arxiv.org/abs/2112.00114
              - [L8] (p.12) .
            - [L7] (p.12) Scott
            - [L7] (p.12) Reed,
            - [L7] (p.12) Konrad
            - [L7] (p.12) Zolna,
            - [L7] (p.12) Emilio
            - [L7] (p.12) Parisotto,
            - [L7] (p.12) Sergio
            - [L7] (p.12) Gomez
            - [L7] (p.12) Colmenarejo,
            - [L7] (p.12) Alexander
            - [L7] (p.12) Novikov,
            - [L7] (p.12) Gabriel Barth-Maron,
            - [L7] (p.12) Mai Gimenez,
            - [L7] (p.12) Yury Sulsky,
            - [L7] (p.12) Jackie Kay,
            - [L7] (p.12) Jost Tobias Springenberg,
            - [L7] (p.12) Tom
            - [L7] (p.12) Eccles,
            - [L7] (p.12) Jake
            - [L7] (p.12) Bruce,
            - [L7] (p.12) Ali
            - [L7] (p.12) Razavi,
            - [L7] (p.12) Ashley
            - [L7] (p.12) Edwards,
            - [L7] (p.12) Nicolas
            - [L7] (p.12) Heess,
            - [L7] (p.12) Yutian
            - [L7] (p.12) Chen,
            - [L7] (p.12) Raia
            - [L7] (p.12) Hadsell,
            - [L7] (p.12) Oriol Vinyals, Mahyar Bordbar, and Nando de Freitas.
            - [L7] (p.12) A generalist agent, 2022.
            - [L7] (p.12) URL
              - [L8] (p.12) https:
              - [L8] (p.12) //arxiv.org/abs/2205.06175
              - [L8] (p.12) .
            - [L7] (p.12) Mohit Shridhar, Jesse Thomason, Daniel Gordon, Yonatan Bisk, Winson Han, Roozbeh Mottaghi,
            - [L7] (p.12) Luke Zettlemoyer, and Dieter Fox.
            - [L7] (p.12) Alfred:
            - [L7] (p.12) A benchmark for interpreting grounded instructions
              - [L8] (p.12) for everyday tasks.
              - [L8] (p.12) In
              - [L8] (p.12) Proceedings of the IEEE/CVF conference on computer vision and pattern
              - [L8] (p.12) recognition
              - [L8] (p.12) , pp. 10740–10749, 2020a.
              - [L8] (p.12) Mohit Shridhar, Xingdi Yuan, Marc-Alexandre Côté, Yonatan Bisk, Adam Trischler, and Matthew
              - [L8] (p.12) Hausknecht.
              - [L8] (p.12) Alfworld:
              - [L8] (p.12) Aligning text and embodied environments for interactive learning.
              - [L8] (p.12) arXiv
              - [L8] (p.12) preprint arXiv:2010.03768
              - [L8] (p.12) , 2020b.
                - [L9] (p.12) Kurt Shuster, Mojtaba Komeili, Leonard Adolphs, Stephen Roller, Arthur Szlam, and Jason Weston.
                - [L9] (p.12) Language models that seek for knowledge:
                - [L9] (p.12) Modular search & generation for dialogue and prompt
              - [L8] (p.12) completion.
              - [L8] (p.12) arXiv preprint arXiv:2203.13224
              - [L8] (p.12) , 2022a.
            - [L7] (p.12) Kurt Shuster, Jing Xu, Mojtaba Komeili, Da Ju, Eric Michael Smith, Stephen Roller, Megan Ung,
              - [L8] (p.12) Moya Chen, Kushal Arora, Joshua Lane, Morteza Behrooz, William Ngan, Spencer Poff, Naman
            - [L7] (p.12) Goyal,
            - [L7] (p.12) Arthur
            - [L7] (p.12) Szlam,
            - [L7] (p.12) Y-Lan
            - [L7] (p.12) Boureau,
            - [L7] (p.12) Melanie
            - [L7] (p.12) Kambadur,
            - [L7] (p.12) and
            - [L7] (p.12) Jason
            - [L7] (p.12) Weston.
            - [L7] (p.12) Blenderbot
            - [L7] (p.12) 3:
            - [L7] (p.12) a
            - [L7] (p.12) deployed
            - [L7] (p.12) conversational
            - [L7] (p.12) agent
            - [L7] (p.12) that
            - [L7] (p.12) continually
            - [L7] (p.12) learns
            - [L7] (p.12) to
            - [L7] (p.12) responsibly
            - [L7] (p.12) engage,
            - [L7] (p.12) 2022b.
            - [L7] (p.12) URL
              - [L8] (p.12) https://arxiv.org/abs/2208.03188
              - [L8] (p.12) .
                - [L9] (p.12) James Thorne, Andreas Vlachos, Christos Christodoulopoulos, and Arpit Mittal.
                - [L9] (p.12) Fever:
                - [L9] (p.12) a large-scale
              - [L8] (p.12) dataset for fact extraction and verification.
              - [L8] (p.12) arXiv preprint arXiv:1803.05355
              - [L8] (p.12) , 2018.
              - [L8] (p.12) Lev S Vygotsky.
              - [L8] (p.12) Thinking and speech.
              - [L8] (p.12) The collected works of LS Vygotsky
              - [L8] (p.12) , 1:39–285, 1987.
                - [L9] (p.12) Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le, Ed Chi, Sharan Narang, Aakanksha Chowdh-
              - [L8] (p.12) ery, and Denny Zhou.
              - [L8] (p.12) Self-consistency improves chain of thought reasoning in language models,
              - [L8] (p.12) 2022a.
              - [L8] (p.12) URL
              - [L8] (p.12) https://arxiv.org/abs/2203.11171
              - [L8] (p.12) .
                - [L9] (p.12) Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le, Ed Chi, and Denny Zhou. Rationale-augmented
              - [L8] (p.12) ensembles in language models.
              - [L8] (p.12) arXiv preprint arXiv:2207.00747
              - [L8] (p.12) , 2022b.
            - [L7] (p.12) Jason
            - [L7] (p.12) Wei,
            - [L7] (p.12) Xuezhi
            - [L7] (p.12) Wang,
            - [L7] (p.12) Dale
            - [L7] (p.12) Schuurmans,
            - [L7] (p.12) Maarten
            - [L7] (p.12) Bosma,
            - [L7] (p.12) Ed
            - [L7] (p.12) Chi,
            - [L7] (p.12) Quoc
            - [L7] (p.12) Le,
            - [L7] (p.12) and
            - [L7] (p.12) Denny
            - [L7] (p.12) Zhou.
            - [L7] (p.12) Chain of thought prompting elicits reasoning in large language models.
            - [L7] (p.12) arXiv preprint
              - [L8] (p.12) arXiv:2201.11903
              - [L8] (p.12) , 2022.
              - [L8] (p.12) Zhilin Yang, Peng Qi, Saizheng Zhang, Yoshua Bengio, William W Cohen, Ruslan Salakhutdinov,
            - [L7] (p.12) and Christopher D Manning.
            - [L7] (p.12) Hotpotqa:
            - [L7] (p.12) A dataset for diverse,
            - [L7] (p.12) explainable multi-hop question
              - [L8] (p.12) answering.
              - [L8] (p.12) arXiv preprint arXiv:1809.09600
              - [L8] (p.12) , 2018.
              - [L8] (p.12) 12
              - [L8] (p.13) Published as a conference paper at ICLR 2023
                - [L9] (p.13) Shunyu Yao, Rohan Rao, Matthew Hausknecht, and Karthik Narasimhan.
                - [L9] (p.13) Keep CALM and explore:
                - [L9] (p.13) Language models for action generation in text-based games. In
                - [L9] (p.13) Proceedings of the 2020 Conference
                - [L9] (p.13) on Empirical Methods in Natural Language Processing (EMNLP)
                - [L9] (p.13) , pp. 8736–8754, Online, Novem-
            - [L7] (p.13) ber 2020. Association for Computational Linguistics.
            - [L7] (p.13) doi:
            - [L7] (p.13) 10.18653/v1/2020.emnlp-main.704.
              - [L8] (p.13) URL
              - [L8] (p.13) https://aclanthology.org/2020.emnlp-main.704
              - [L8] (p.13) .
            - [L7] (p.13) Shunyu
            - [L7] (p.13) Yao,
            - [L7] (p.13) Howard
            - [L7] (p.13) Chen,
            - [L7] (p.13) John
            - [L7] (p.13) Yang,
            - [L7] (p.13) and
            - [L7] (p.13) Karthik
            - [L7] (p.13) Narasimhan.
            - [L7] (p.13) Webshop:
            - [L7] (p.13) Towards
            - [L7] (p.13) scalable
            - [L7] (p.13) real-world
            - [L7] (p.13) web
            - [L7] (p.13) interaction
            - [L7] (p.13) with
            - [L7] (p.13) grounded
            - [L7] (p.13) language
            - [L7] (p.13) agents.
            - [L7] (p.13) arXiv
            - [L7] (p.13) preprint
            - [L7] (p.13) arXiv:2207.01206
            - [L7] (p.13) ,
              - [L8] (p.13) 2022.
              - [L8] (p.13) Eric Zelikman, Yuhuai Wu, Jesse Mu, and Noah D. Goodman.
              - [L8] (p.13) Star:
              - [L8] (p.13) Bootstrapping reasoning with
              - [L8] (p.13) reasoning, 2022.
              - [L8] (p.13) URL
              - [L8] (p.13) https://arxiv.org/abs/2203.14465
              - [L8] (p.13) .
                - [L9] (p.13) Denny Zhou, Nathanael Schärli, Le Hou, Jason Wei, Nathan Scales, Xuezhi Wang, Dale Schuurmans,
              - [L8] (p.13) Olivier Bousquet, Quoc Le, and Ed Chi.
              - [L8] (p.13) Least-to-most prompting enables complex reasoning in
              - [L8] (p.13) large language models, 2022.
              - [L8] (p.13) URL
              - [L8] (p.13) https://arxiv.org/abs/2205.10625
              - [L8] (p.13) .
            - [L7] (p.13) Yunchang Zhu, Liang Pang, Yanyan Lan, Huawei Shen, and Xueqi Cheng.
            - [L7] (p.13) Adaptive information
              - [L8] (p.13) seeking for open-domain question answering.
              - [L8] (p.13) arXiv preprint arXiv:2109.06747
              - [L8] (p.13) , 2021.
              - [L8] (p.13) 13
              - [L8] (p.14) Published as a conference paper at ICLR 2023
      - [L4] (p.14) A
      - [L4] (p.14) A
                    - [L11] (p.14) DDITIONAL
      - [L4] (p.14) R
                    - [L11] (p.14) ESULTS
              - [L8] (p.14) A.1
              - [L8] (p.14) GPT-3
              - [L8] (p.14) E
                                - [L17] (p.14) XPERIMENTS
              - [L8] (p.14) PaLM-540B
              - [L8] (p.14) GPT-3
              - [L8] (p.14) HotpotQA (exact match)
              - [L8] (p.14) 29.4
              - [L8] (p.14) 30.8
              - [L8] (p.14) ALFWorld (success rate %)
              - [L8] (p.14) 70.9
              - [L8] (p.14) 78.4
                - [L9] (p.14) Table 5:
              - [L8] (p.14) ReAct
                - [L9] (p.14) prompting results using PaLM-540B vs. GPT-3 (text-davinci-002, greedy decoding).
                - [L9] (p.14) On HotpotQA, we randomly sample a subset of 500 validation questions.
                - [L9] (p.14) On ALFWorld, we use all
              - [L8] (p.14) 134 unseen validation task instances, and use the best prompt set according to PaLM-540B.
                - [L9] (p.14) We run additional GPT-3 (Brown et al., 2020) experiments to confirm
              - [L8] (p.14) ReAct
                - [L9] (p.14) prompting performance
            - [L7] (p.14) is general across different large language models.
            - [L7] (p.14) As shown in Table 5, GPT-3 (text-davinci-002,
            - [L7] (p.14) greedy
            - [L7] (p.14) decoding)
            - [L7] (p.14) consistently
            - [L7] (p.14) outperforms
            - [L7] (p.14) PaLM-540B
            - [L7] (p.14) on
            - [L7] (p.14) HotpotQA
            - [L7] (p.14) and
            - [L7] (p.14) ALFWorld,
            - [L7] (p.14) possibly
                - [L9] (p.14) because it is finetuned with human instruction following.
                - [L9] (p.14) This indicates ReAct prompting is effective
            - [L7] (p.14) across
            - [L7] (p.14) different
            - [L7] (p.14) large
            - [L7] (p.14) language
            - [L7] (p.14) models
            - [L7] (p.14) on
            - [L7] (p.14) different
            - [L7] (p.14) tasks.
            - [L7] (p.14) The
            - [L7] (p.14) code
            - [L7] (p.14) for
            - [L7] (p.14) these
            - [L7] (p.14) experiments
            - [L7] (p.14) are
            - [L7] (p.14) at
              - [L8] (p.14) https://react-lm.github.io/
              - [L8] (p.14) .
              - [L8] (p.14) A.2
              - [L8] (p.14) R
                                - [L17] (p.14) E
              - [L8] (p.14) A
                                - [L17] (p.14) CT
                                - [L17] (p.14) OBTAINS
                                - [L17] (p.14) UP
              - [L8] (p.14) -
                                - [L17] (p.14) TO
              - [L8] (p.14) -
                                - [L17] (p.14) DATE
                                - [L17] (p.14) KNOWLEDGE
                                - [L17] (p.14) ON
              - [L8] (p.14) H
                                - [L17] (p.14) OTPOT
              - [L8] (p.14) QA
        - [L5] (p.14) �
                - [L9] (p.14) Figure 4:
                - [L9] (p.14) Another example HotpotQA question, where the original label is outdated.
                - [L9] (p.14) Only
              - [L8] (p.14) ReAct
                - [L9] (p.14) is
              - [L8] (p.14) able to obtain the up-to-date answer thanks to real-world web interaction plus reasoning.
                - [L9] (p.14) During trajectory inspection, we also find that sometimes
              - [L8] (p.14) ReAct
                - [L9] (p.14) does not agree with dataset labels as
                - [L9] (p.14) the labels themselves could be outdated.
                - [L9] (p.14) For example, as shown in Figure 4, the question asks about
                - [L9] (p.14) the size of a hotel, which increased from the HotpotQA construction time. While
              - [L8] (p.14) Standard
                - [L9] (p.14) and
              - [L8] (p.14) CoT
              - [L8] (p.14) give wrong answers due to hallucination,
              - [L8] (p.14) Act
              - [L8] (p.14) fails despite the access of real-world web interaction,
              - [L8] (p.14) due to a lack of reasoning to guide how to interact with the Internet for QA. Only
              - [L8] (p.14) ReAct
              - [L8] (p.14) is able to
                - [L9] (p.14) retrieve up-to-date information from the Internet and provide a reasonable answer.
                - [L9] (p.14) Therefore, better
                - [L9] (p.14) incorporation of reasoning abilities might benefit recent Internet-augmented language models (Nakano
              - [L8] (p.14) et al., 2021; Lazaridou et al., 2022; Shuster et al., 2022a) for up-to-date task solving.
              - [L8] (p.14) A.3
              - [L8] (p.14) H
                                - [L17] (p.14) UMAN
              - [L8] (p.14) -
                                - [L17] (p.14) IN
              - [L8] (p.14) -
                                - [L17] (p.14) THE
              - [L8] (p.14) -
                                - [L17] (p.14) LOOP
                                - [L17] (p.14) BEHAVIOR
                                - [L17] (p.14) CORRECTION
                                - [L17] (p.14) ON
              - [L8] (p.14) A
                                - [L17] (p.14) LF
              - [L8] (p.14) W
                                - [L17] (p.14) ORLD
            - [L7] (p.14) We also explore human-in-the-loop interaction with
              - [L8] (p.14) ReAct
            - [L7] (p.14) , to allow a human to inspect and edit
              - [L8] (p.14) ReAct
              - [L8] (p.14) ’s reasoning traces.
              - [L8] (p.14) Figure 5 shows that by simply removing a hallucinating sentence in Act
              - [L8] (p.14) 17 and adding some hints in Act 23,
              - [L8] (p.14) ReAct
              - [L8] (p.14) can be made to change its behavior drastically to align
              - [L8] (p.14) with these human thought edits and succeed in the task.
              - [L8] (p.14) From a human perspective, solving such a
            - [L7] (p.14) task becomes significantly easier, from typing tens of actions to only editing a couple of thoughts,
                - [L9] (p.14) which enables new forms of human-machine collaboration.
                - [L9] (p.14) We note that such a policy edit on-the-go
              - [L8] (p.14) 14
              - [L8] (p.15) Published as a conference paper at ICLR 2023
                  - [L10] (p.15) �
              - [L8] (p.15) Figure 5:
              - [L8] (p.15) A human-in-the-loop behavior correction example with
              - [L8] (p.15) ReAct
              - [L8] (p.15) in AlfWorld.
              - [L8] (p.15) (a)
              - [L8] (p.15) ReAct
                - [L9] (p.15) trajectory fails due to a hallucinating thought (Act 17).
                - [L9] (p.15) (b) By a human simply editing two thoughts
              - [L8] (p.15) (Act 17, 23), the
              - [L8] (p.15) ReAct
              - [L8] (p.15) trajectory produces desirable reasoning traces and actions and succeeds.
                - [L9] (p.15) is difficult for
              - [L8] (p.15) Act
                - [L9] (p.15) and previous RL methods, as a human cannot change the model parameters, and
                - [L9] (p.15) changing a few actions might not edit the rest of the model behavior.
                - [L9] (p.15) This paradigm is also more than
            - [L7] (p.15) human dialogue to update the goal or subgoal as in Huang et al. (2022b) — while editing
              - [L8] (p.15) ReAct
                - [L9] (p.15) thoughts can do these, it can also modify the model’s internal belief, reasoning styles, or anything the
            - [L7] (p.15) flexible thought space supports, for better task solving.
            - [L7] (p.15) We believe this is an exciting direction for
              - [L8] (p.15) human alignment and leave more systematic study as future work.
      - [L4] (p.15) B
      - [L4] (p.15) E
                    - [L11] (p.15) XPERIMENT
      - [L4] (p.15) D
                    - [L11] (p.15) ETAILS
              - [L8] (p.15) B.1
              - [L8] (p.15) H
                                - [L17] (p.15) OTPOT
              - [L8] (p.15) QA
              - [L8] (p.15) F
                                - [L17] (p.15) INETUNING
              - [L8] (p.15) D
                                - [L17] (p.15) ETAILS
            - [L7] (p.15) For all finetuning we use a batch size of 64.
            - [L7] (p.15) On PaLM-8B, we finetune
              - [L8] (p.15) ReAct
            - [L7] (p.15) and
              - [L8] (p.15) Act
            - [L7] (p.15) methods
            - [L7] (p.15) for
              - [L8] (p.15) 4
              - [L8] (p.15) ,
              - [L8] (p.15) 000
            - [L7] (p.15) steps
            - [L7] (p.15) and
              - [L8] (p.15) Standard
            - [L7] (p.15) and
              - [L8] (p.15) CoT
            - [L7] (p.15) methods
            - [L7] (p.15) for
              - [L8] (p.15) 2
              - [L8] (p.15) ,
              - [L8] (p.15) 000
            - [L7] (p.15) steps.
            - [L7] (p.15) On
            - [L7] (p.15) PaLM-62B,
            - [L7] (p.15) we
            - [L7] (p.15) finetune
              - [L8] (p.15) ReAct
            - [L7] (p.15) and
              - [L8] (p.15) Act
            - [L7] (p.15) methods for
              - [L8] (p.15) 4
              - [L8] (p.15) ,
              - [L8] (p.15) 000
            - [L7] (p.15) steps and
              - [L8] (p.15) Standard
            - [L7] (p.15) and
              - [L8] (p.15) CoT
            - [L7] (p.15) methods for
              - [L8] (p.15) 1
              - [L8] (p.15) ,
              - [L8] (p.15) 000
            - [L7] (p.15) steps.
            - [L7] (p.15) We
              - [L8] (p.15) find
              - [L8] (p.15) ReAct
              - [L8] (p.15) and
              - [L8] (p.15) Act
              - [L8] (p.15) methods generally benefit from more training steps (and more training data),
              - [L8] (p.15) while
              - [L8] (p.15) Standard
              - [L8] (p.15) and
              - [L8] (p.15) CoT
              - [L8] (p.15) methods degrade soon after finetuning.
              - [L8] (p.15) B.2
              - [L8] (p.15) A
                                - [L17] (p.15) LF
              - [L8] (p.15) W
                                - [L17] (p.15) ORLD
              - [L8] (p.15) IM-S
                                - [L17] (p.15) TYLE
              - [L8] (p.15) D
                                - [L17] (p.15) ETAILS
            - [L7] (p.15) For the IM-style ablation, the same expert trajectories used in
              - [L8] (p.15) ReAct
            - [L7] (p.15) are reannotated with dense
            - [L7] (p.15) external feedback thoughts within these trajectories, that limit
              - [L8] (p.15) ReAct-IM
            - [L7] (p.15) to only think about (1)
              - [L8] (p.15) decomposing the current goal and (2) the current subgoal that needs to be completed.
              - [L8] (p.15) In particular,
              - [L8] (p.15) ReAct-IM
              - [L8] (p.15) lacks thoughts that (1) determine when a subgoal is completed (2) determine what the
                - [L9] (p.15) next subgoal should be (3) inducing the LLM to refer to its internal pretraining knowledge to identify
              - [L8] (p.15) where items can be within the environment.
              - [L8] (p.15) 15
              - [L8] (p.16) Published as a conference paper at ICLR 2023
      - [L4] (p.16) C
      - [L4] (p.16) P
                    - [L11] (p.16) ROMPTS
              - [L8] (p.16) C.1
              - [L8] (p.16) H
                                - [L17] (p.16) OTPOT
              - [L8] (p.16) QA
              - [L8] (p.16) 16
              - [L8] (p.17) Published as a conference paper at ICLR 2023
              - [L8] (p.17) 17
              - [L8] (p.18) Published as a conference paper at ICLR 2023
              - [L8] (p.18) 18
              - [L8] (p.19) Published as a conference paper at ICLR 2023
              - [L8] (p.19) 19
              - [L8] (p.20) Published as a conference paper at ICLR 2023
              - [L8] (p.20) C.2
              - [L8] (p.20) F
                                - [L17] (p.20) EVER
              - [L8] (p.20) 20
              - [L8] (p.21) Published as a conference paper at ICLR 2023
              - [L8] (p.21) 21
              - [L8] (p.22) Published as a conference paper at ICLR 2023
              - [L8] (p.22) C.3
              - [L8] (p.22) W
                                - [L17] (p.22) EBSHOP
              - [L8] (p.22) Table 6:
              - [L8] (p.22) Prompts used for the Webshop experiments in Section 4.
              - [L8] (p.22) We use the prompt on the left for
              - [L8] (p.22) Act
              - [L8] (p.22) , and use the prompt on the right (add reasoning) for
              - [L8] (p.22) ReAct
              - [L8] (p.22) .
              - [L8] (p.22) 22
              - [L8] (p.23) Published as a conference paper at ICLR 2023
              - [L8] (p.23) C.4
              - [L8] (p.23) ALFW
                                - [L17] (p.23) ORLD
              - [L8] (p.23) Table 7:
              - [L8] (p.23) An
              - [L8] (p.23) Act
              - [L8] (p.23) prompt on the ALFWorld clean task.
              - [L8] (p.23) No thoughts are provided.
              - [L8] (p.23) 23
              - [L8] (p.24) Published as a conference paper at ICLR 2023
              - [L8] (p.24) Table 8:
              - [L8] (p.24) An
              - [L8] (p.24) ReAct
              - [L8] (p.24) prompt on the ALFWorld clean task.
              - [L8] (p.24) 24
              - [L8] (p.25) Published as a conference paper at ICLR 2023
              - [L8] (p.25) Table 9:
              - [L8] (p.25) An
              - [L8] (p.25) ReAct-IM
              - [L8] (p.25) prompt on the ALFWorld clean task.
      - [L4] (p.25) D
      - [L4] (p.25) T
                    - [L11] (p.25) RAJECTORIES
              - [L8] (p.25) D.1
              - [L8] (p.25) FEVER
              - [L8] (p.25) T
                                - [L17] (p.25) RAJECTORIES
                - [L9] (p.25) We provide some trajectories produced by
              - [L8] (p.25) ReAct
                - [L9] (p.25) ,
              - [L8] (p.25) CoT
                - [L9] (p.25) and
              - [L8] (p.25) Act
                - [L9] (p.25) on several randomly selected exam-
              - [L8] (p.25) ples from the FEVER dev set below.
              - [L8] (p.25) Search results are omitted to space.
              - [L8] (p.25) 25
              - [L8] (p.26) Published as a conference paper at ICLR 2023
              - [L8] (p.26) 26
              - [L8] (p.27) Published as a conference paper at ICLR 2023
              - [L8] (p.27) D.2
              - [L8] (p.27) ALFW
                                - [L17] (p.27) ORLD
              - [L8] (p.27) T
                                - [L17] (p.27) RAJECTORIES
            - [L7] (p.27) We provide an example trajectory of
              - [L8] (p.27) ReAct
            - [L7] (p.27) ,
              - [L8] (p.27) Act
            - [L7] (p.27) , and
              - [L8] (p.27) ReAct-IM
            - [L7] (p.27) on the same ALFWorld game,
              - [L8] (p.27) pick_clean_then_place_in_recep-Knife-None-CounterTop-10/
              - [L8] (p.27) trial_T20190909_110445_675754
              - [L8] (p.27) .
              - [L8] (p.27) D.2.1
              - [L8] (p.27) R
                                - [L17] (p.27) E
              - [L8] (p.27) A
                                - [L17] (p.27) CT
                                - [L17] (p.27) TRAJECTORY
              - [L8] (p.27) ReAct
              - [L8] (p.27) is able to correctly find the knife, clean it, and then place it on a countertop.
              - [L8] (p.27) 27
              - [L8] (p.28) Published as a conference paper at ICLR 2023
              - [L8] (p.28) D.2.2
              - [L8] (p.28) A
                                - [L17] (p.28) CT
                                - [L17] (p.28) TRAJECTORY
              - [L8] (p.28) Act
            - [L7] (p.28) is able to correctly find the knife, but tries to clean it using a sinkbasin before actually going
            - [L7] (p.28) to
            - [L7] (p.28) the
            - [L7] (p.28) sinkbasin.
            - [L7] (p.28) From
            - [L7] (p.28) there
            - [L7] (p.28) on,
            - [L7] (p.28) the
            - [L7] (p.28) model
            - [L7] (p.28) is
            - [L7] (p.28) unable
            - [L7] (p.28) to
            - [L7] (p.28) recover,
            - [L7] (p.28) and
            - [L7] (p.28) is
            - [L7] (p.28) stuck
            - [L7] (p.28) repeating
            - [L7] (p.28) the
            - [L7] (p.28) same
              - [L8] (p.28) sequence of commands.
              - [L8] (p.28) With
              - [L8] (p.28) ReAct
              - [L8] (p.28) , an existing thought would have concretely identified that the
              - [L8] (p.28) knife had been taken, and that the next subgoal was to go to a sinkbasin to clean it.
              - [L8] (p.28) 28
              - [L8] (p.29) Published as a conference paper at ICLR 2023
              - [L8] (p.29) D.2.3
              - [L8] (p.29) R
                                - [L17] (p.29) E
              - [L8] (p.29) A
                                - [L17] (p.29) CT
              - [L8] (p.29) -IM
                                - [L17] (p.29) TRAJECTORY
              - [L8] (p.29) ReAct-IM
            - [L7] (p.29) is
            - [L7] (p.29) able
            - [L7] (p.29) to
            - [L7] (p.29) correctly
            - [L7] (p.29) find
            - [L7] (p.29) the
            - [L7] (p.29) knife,
            - [L7] (p.29) but
            - [L7] (p.29) is
            - [L7] (p.29) unable
            - [L7] (p.29) to
            - [L7] (p.29) clean
            - [L7] (p.29) it
            - [L7] (p.29) as
            - [L7] (p.29) well.
            - [L7] (p.29) The
            - [L7] (p.29) LLM
            - [L7] (p.29) then
            - [L7] (p.29) gets
            - [L7] (p.29) stuck
            - [L7] (p.29) trying
            - [L7] (p.29) to
            - [L7] (p.29) place
            - [L7] (p.29) this
            - [L7] (p.29) knife
            - [L7] (p.29) on
            - [L7] (p.29) a
            - [L7] (p.29) countertop.
            - [L7] (p.29) One
            - [L7] (p.29) possible
            - [L7] (p.29) issue
            - [L7] (p.29) is
            - [L7] (p.29) the
            - [L7] (p.29) incorrect
            - [L7] (p.29) thought
              - [L8] (p.29) think:
              - [L8] (p.29) I
              - [L8] (p.29) need
              - [L8] (p.29) to
              - [L8] (p.29) find
              - [L8] (p.29) a
              - [L8] (p.29) clean
              - [L8] (p.29) knife.
              - [L8] (p.29) , which seems to trick the LLM in believing
                - [L9] (p.29) that the knife is already cleaned.
                - [L9] (p.29) In
              - [L8] (p.29) ReAct
                - [L9] (p.29) , this sequence of subgoals would be concretely captured
              - [L8] (p.29) by each thought.
              - [L8] (p.29) 29
              - [L8] (p.30) Published as a conference paper at ICLR 2023
              - [L8] (p.30) 30
              - [L8] (p.31) Published as a conference paper at ICLR 2023
              - [L8] (p.31) D.3
              - [L8] (p.31) W
                                - [L17] (p.31) EBSHOP
              - [L8] (p.31) T
                                - [L17] (p.31) RAJECTORIES
            - [L7] (p.31) Table
            - [L7] (p.31) 10:
            - [L7] (p.31) Example
            - [L7] (p.31) trajectories
            - [L7] (p.31) for
            - [L7] (p.31) Webshop
            - [L7] (p.31) predicted
            - [L7] (p.31) by
              - [L8] (p.31) Act
            - [L7] (p.31) and
              - [L8] (p.31) ReAct
            - [L7] (p.31) .
            - [L7] (p.31) Compared
            - [L7] (p.31) to
              - [L8] (p.31) Act
            - [L7] (p.31) ,
              - [L8] (p.31) ReAct
              - [L8] (p.31) uses reasoning to find products that satisfy all target attributes.
              - [L8] (p.31) 31
              - [L8] (p.32) Published as a conference paper at ICLR 2023
      - [L4] (p.32) E
      - [L4] (p.32) M
                    - [L11] (p.32) ORE
      - [L4] (p.32) A
                    - [L11] (p.32) NALYSIS
              - [L8] (p.32) E.1
              - [L8] (p.32) S
                                - [L17] (p.32) UCCESS
                                - [L17] (p.32) AND
              - [L8] (p.32) F
                                - [L17] (p.32) AILURE
              - [L8] (p.32) M
                                - [L17] (p.32) ODES
              - [L8] (p.32) A
                                - [L17] (p.32) NALYSIS
              - [L8] (p.32) We provide some examples corresponding to the success and error mode analysis given in Sec. 3.3.
              - [L8] (p.32) Search results and non-representative steps are omitted to reduce space.
              - [L8] (p.32) 32
              - [L8] (p.33) Published as a conference paper at ICLR 2023
              - [L8] (p.33) 33

## 📊 各页概况

| 页码 | 文本长度 | 文本块数 | 图片数 | 含矢量图 |
|------|----------|----------|--------|----------|
| 1 | 3601 | 12 | 0 | ✓ |
| 2 | 5779 | 37 | 0 | ✓ |
| 3 | 5208 | 9 | 0 | ✓ |
| 4 | 4297 | 12 | 0 | ✓ |
| 5 | 3680 | 34 | 0 | ✓ |
| 6 | 4643 | 15 | 0 | ✓ |
| 7 | 4075 | 22 | 0 | ✓ |
| 8 | 4131 | 17 | 0 | ✓ |
| 9 | 4996 | 9 | 0 | ✓ |
| 10 | 3811 | 15 | 0 | ✓ |
| 11 | 3748 | 16 | 0 | ✓ |
| 12 | 3792 | 18 | 0 | ✓ |
| 13 | 1222 | 7 | 0 | ✓ |
| 14 | 4367 | 32 | 0 | ✓ |
| 15 | 4297 | 13 | 0 | ✓ |
| 16 | 3323 | 16 | 0 | ✓ |
| 17 | 3984 | 13 | 0 | ✓ |
| 18 | 4377 | 9 | 0 | ✓ |
| 19 | 645 | 4 | 0 | ✓ |
| 20 | 3261 | 16 | 0 | ✓ |
| 21 | 3553 | 8 | 0 | ✓ |
| 22 | 3277 | 36 | 0 | ✓ |
| 23 | 1738 | 5 | 0 | ✓ |
| 24 | 2189 | 4 | 0 | ✓ |
| 25 | 2404 | 7 | 0 | ✓ |
| 26 | 2684 | 5 | 0 | ✓ |
| 27 | 1124 | 7 | 0 | ✓ |
| 28 | 2662 | 6 | 0 | ✓ |
| 29 | 3266 | 6 | 0 | ✓ |
| 30 | 2034 | 4 | 0 | ✓ |
| 31 | 2960 | 37 | 0 | ✓ |
| 32 | 3274 | 8 | 0 | ✓ |
| 33 | 1834 | 5 | 0 | ✓ |

---

## 📖 全文内容


---
### 【第 1 页】


###### Published as a conference paper at ICLR 2023


##### REACT: SYNERGIZING REASONING AND ACTING IN


##### LANGUAGE MODELS


###### Shunyu Yao∗*,1, Jeffrey Zhao2, Dian Yu2, Nan Du2, Izhak Shafran2, Karthik Narasimhan1, Yuan Cao2


###### 1Department of Computer Science, Princeton University


###### 2Google Research, Brain team


###### 1{shunyuy,karthikn}@princeton.edu


###### 2{jeffreyzhao,dianyu,dunan,izhak,yuancao}@google.com


###### ABSTRACT


###### While large language models (LLMs) have demonstrated impressive performance


###### across tasks in language understanding and interactive decision making, their


###### abilities for reasoning (e.g. chain-of-thought prompting) and acting (e.g. action


###### plan generation) have primarily been studied as separate topics. In this paper, we


###### explore the use of LLMs to generate both reasoning traces and task-specific actions


###### in an interleaved manner, allowing for greater synergy between the two: reasoning


###### traces help the model induce, track, and update action plans as well as handle


###### exceptions, while actions allow it to interface with and gather additional information


###### from external sources such as knowledge bases or environments. We apply our


###### approach, named ReAct, to a diverse set of language and decision making tasks


###### and demonstrate its effectiveness over state-of-the-art baselines in addition to


###### improved human interpretability and trustworthiness. Concretely, on question


###### answering (HotpotQA) and fact verification (Fever), ReAct overcomes prevalent


###### issues of hallucination and error propagation in chain-of-thought reasoning by


###### interacting with a simple Wikipedia API, and generating human-like task-solving


###### trajectories that are more interpretable than baselines without reasoning traces.


###### Furthermore, on two interactive decision making benchmarks (ALFWorld and


###### WebShop), ReAct outperforms imitation and reinforcement learning methods by


###### an absolute success rate of 34% and 10% respectively, while being prompted with


###### only one or two in-context examples.


###### 1


###### INTRODUCTION


###### A unique feature of human intelligence is the ability to seamlessly combine task-oriented actions with


###### verbal reasoning (or inner speech, Alderson-Day & Fernyhough, 2015), which has been theorized to


###### play an important role in human cognition for enabling self-regulation or strategization (Vygotsky,


###### 1987; Luria, 1965; Fernyhough, 2010) and maintaining a working memory (Baddeley, 1992). Con-


###### sider the example of cooking up a dish in the kitchen. Between any two specific actions, we may


###### reason in language in order to track progress (“now that everything is cut, I should heat up the pot of


###### water”), to handle exceptions or adjust the plan according to the situation (“I don’t have salt, so let


###### me use soy sauce and pepper instead”), and to realize when external information is needed (“how do


###### I prepare dough? Let me search on the Internet”). We may also act (open a cookbook to read the


###### recipe, open the fridge, check ingredients) to support the reasoning and to answer questions (“What


###### dish can I make right now?”). This tight synergy between “acting” and “reasoning” allows humans


###### to learn new tasks quickly and perform robust decision making or reasoning, even under previously


###### unseen circumstances or facing information uncertainties.


###### Recent results have hinted at the possibility of combining verbal reasoning with interactive decision


###### making in autonomous systems. On one hand, properly prompted large language models (LLMs)


###### have demonstrated emergent capabilities to carry out several steps of reasoning traces to derive


###### ∗Work during Google internship. Projet page with code: https://react-lm.github.io/.


###### 1


#### arXiv:2210.03629v3  [cs.CL]  10 Mar 2023


---
### 【第 2 页】


###### Published as a conference paper at ICLR 2023

���������������������������������������������������������
����������������������������������������������������������
��
�����������������������
�������������������������������������������
����������������������������������������������������������������������������
��������������������������
���������������������������������������������������������
�
���������������������������������������
����������������������������������������������
�������������������������������������������������������������
�
����������������������������������������������������������
�
�����������������������
����������������������
���������������������������
����������������������
���������������������������
�������������������������������������������
���������������������������������������������������
�������������
������������
����������������������
��������������������������
��������������������������
�����������������������
������������������������
���������������������������
��������������������������
������������������������
�����������������������
������
���������������������������
�����
��������������
����������������������������
�����������������������������
����������������
�������������������������
�����������������������������
����������������
������������������������
������������
����������������������
��������������������������
����������
������������������
�������������������������
������������������������������������������������������
����������������������������������������������������
���������������������������
���������������������������������������������������������
�
����������������������������������������������������������
�
��������������������������������
����������������������������������������������������������
�
�����������������������������������������������������
������
���������������������������������������������������
������������������������
�������������������������������������������������������
�
���������������������������������������������������
���������������
����������������������������������������������������������
����������������
�����������������������������������
����������������������������������������������������������
���������������������������������������������������������
�
�������������������������������������������������������
�����������������������
�������������������������������������

###### �

��������������������������������������������������������
�
���������������������������������������������������
�
��������������������������
��������������
����������������������
�������������������������������
���������������������
����������������������������������������������������������
�
��������������������������������������
�
�������������������������
����������������������������������������������������
�
��������������������������
��������������������������������������������
������������������������
��������������������������������������������
������������������������
�������������������������

###### �

�������������������������������������������������������
�
����������������������������������������������������������
�
���������������������������������������������������
�
����������������������������������������������������
������������
��������������

###### Figure 1: (1) Comparison of 4 prompting methods, (a) Standard, (b) Chain-of-thought (CoT,


###### Reason Only), (c) Act-only, and (d) ReAct (Reason+Act), solving a HotpotQA (Yang et al., 2018)


###### question. (2) Comparison of (a) Act-only and (b) ReAct prompting to solve an AlfWorld (Shridhar


###### et al., 2020b) game. In both domains, we omit in-context examples in the prompt, and only show task


###### solving trajectories generated by the model (Act, Thought) and the environment (Obs).


###### answers from questions in arithmetic, commonsense, and symbolic reasoning tasks (Wei et al.,


###### 2022). However, this “chain-of-thought” reasoning is a static black box, in that the model uses


###### its own internal representations to generate thoughts and is not grounded in the external world,


###### which limits its ability to reason reactively or update its knowledge. This can lead to issues like fact


###### hallucination and error propagation over the reasoning process (Figure 1 (1b)). On the other hand,


###### recent work has explored the use of pre-trained language models for planning and acting in interactive


###### environments (Ahn et al., 2022; Nakano et al., 2021; Yao et al., 2020; Huang et al., 2022a), with


###### a focus on predicting actions via language priors. These approaches usually convert multi-modal


###### observations into text, use a language model to generate domain-specific actions or plans, and then


###### use a controller to choose or execute them. However, they do not employ language models to reason


###### abstractly about high-level goals or maintain a working memory to support acting, barring Huang


###### et al. (2022b) who perform a limited form of verbal reasoning to reiterate spatial facts about the


###### current state. Beyond such simple embodied tasks to interact with a few blocks, there have not been


###### studies on how reasoning and acting can be combined in a synergistic manner for general task solving,


###### and if such a combination can bring systematic benefits compared to reasoning or acting alone.


###### In this work, we present ReAct, a general paradigm to combine reasoning and acting with language


###### models for solving diverse language reasoning and decision making tasks (Figure 1). ReAct


###### prompts LLMs to generate both verbal reasoning traces and actions pertaining to a task in an


###### interleaved manner, which allows the model to perform dynamic reasoning to create, maintain, and


###### adjust high-level plans for acting (reason to act), while also interact with the external environments


###### (e.g. Wikipedia) to incorporate additional information into reasoning (act to reason).


###### 2


---
### 【第 3 页】


###### Published as a conference paper at ICLR 2023


###### We conduct empirical evaluations of ReAct and state-of-the-art baselines on four diverse benchmarks:


###### question answering (HotPotQA, Yang et al., 2018), fact verification (Fever, Thorne et al., 2018),


###### text-based game (ALFWorld, Shridhar et al., 2020b), and webpage navigation (WebShop, Yao


###### et al., 2022). For HotPotQA and Fever, with access to a Wikipedia API that the model can interact


###### with, ReAct outperforms vanilla action generation models while being competitive with chain-of-


###### thought reasoning (CoT) (Wei et al., 2022). The best approach overall is a combination of ReAct


###### and CoT that allows for the use of both internal knowledge and externally obtained information


###### during reasoning. On ALFWorld and WebShop, two or even one-shot ReAct prompting is able


###### to outperform imitation or reinforcement learning methods trained with 103 ∼105 task instances,


###### with an absolute improvement of 34% and 10% in success rates respectively. We also demonstrate


###### the importance of sparse, versatile reasoning in decision making by showing consistent advantages


###### over controlled baselines with actions only. Besides general applicability and performance boost,


###### the combination of reasoning and acting also contributes to model interpretability, trustworthiness,


###### and diagnosability across all domains, as humans can readily distinguish information from model’s


###### internal knowledge versus external environments, as well as inspect reasoning traces to understand


###### the decision basis of model actions.


###### To summarize, our key contributions are the following: (1) we introduce ReAct, a novel prompt-


###### based paradigm to synergize reasoning and acting in language models for general task solving; (2) we


###### perform extensive experiments across diverse benchmarks to showcase the advantage of ReAct in a


###### few-shot learning setup over prior approaches that perform either reasoning or action generation in


###### isolation; (3) we present systematic ablations and analysis to understand the importance of acting in


###### reasoning tasks, and reasoning in interactive tasks; (4) we analyze the limitations of ReAct under the


###### prompting setup (i.e. limited support of reasoning and acting behaviors), and perform initial finetuning


###### experiments showing the potential of ReAct to improve with additional training data. Scaling up


###### ReAct to train and operate on more tasks and combining it with complementary paradigms like


###### reinforcement learning could further unlock the potential of large language models.


###### 2


###### REAC T: SYNERGIZING REASONING + ACTING


###### Consider a general setup of an agent interacting with an environment for task solving. At time


###### step t, an agent receives an observation ot ∈O from the environment and takes an action at ∈A


###### following some policy π(at|ct), where ct = (o1, a1, · · · , ot−1, at−1, ot) is the context to the agent.


###### Learning a policy is challenging when the mapping ct �→at is highly implicit and requires extensive


###### computation. For example, the agent shown in Figure 1(1c) is unable to generate the correct final


###### action (Act 4) to finish the QA task as it requires complex reasoning over the trajectory context


###### (Question, Act 1-3, Obs 1-3). Similarly, the agent shown in Figure 1(2a) fails to comprehend from the


###### context that sinkbasin 1 does not contain peppershaker 1, thus keep producing hallucinating actions.


###### The idea of ReAct is simple: we augment the agent’s action space to ˆ


###### A = A ∪L, where L is the


###### space of language. An action ˆat ∈L in the language space, which we will refer to as a thought or a


###### reasoning trace, does not affect the external environment, thus leading to no observation feedback.


###### Instead, a thought ˆat aims to compose useful information by reasoning over the current context ct,


###### and update the context ct+1 = (ct, ˆat) to support future reasoning or acting. As shown in Figure 1,


###### there could be various types of useful thoughts, e.g. decomposing task goals and create action plans


###### (2b, Act 1; 1d, Thought 1), injecting commonsense knowledge relevant to task solving (2b, Act 1),


###### extracting important parts from observations (1d, Thought2, 4), track progress and transit action plans


###### (2b, Act 8), handle exceptions and adjust action plans (1d, Thought 3), and so on.


###### However, as the language space L is unlimited, learning in this augmented action space is difficult


###### and requires strong language priors. In this paper, we mainly focus on the setup where a frozen


###### large language model, PaLM-540B (Chowdhery et al., 2022)1, is prompted with few-shot in-context


###### examples to generate both domain-specific actions and free-form language thoughts for task solving


###### (Figure 1 (1d), (2b)). Each in-context example is a human trajectory of actions, thoughts, and


###### environment observations to solve a task instance (see Appendix C). For the tasks where reasoning is


###### of primary importance (Figure 1(1)), we alternate the generation of thoughts and actions so that the


###### task-solving trajectory consists of multiple thought-action-observation steps. In contrast, for decision


###### making tasks that potentially involve a large number of actions (Figure 1(2)), thoughts only need to


###### 1We show some GPT-3 (Brown et al., 2020) results in Appendix A.1, which outperforms PaLM-540B.


###### 3


---
### 【第 4 页】


###### Published as a conference paper at ICLR 2023


###### appear sparsely in the most relevant positions of a trajectory, so we let the language model decide the


###### asynchronous occurrence of thoughts and actions for itself.


###### Since decision making and reasoning capabilities are integrated into a large language model, ReAct


###### enjoys several unique features: A) Intuitive and easy to design: Designing ReAct prompts is


###### straightforward as human annotators just type down their thoughts in language on top of their actions


###### taken. No ad-hoc format choice, thought design, or example selection is used in this paper. We detail


###### prompt design for each task in Sections 3 and 4. B) General and flexible: Due to the flexible thought


###### space and thought-action occurrence format, ReAct works for diverse tasks with distinct action


###### spaces and reasoning needs, including but not limited to QA, fact verification, text game, and web


###### navigation. C) Performant and robust: ReAct shows strong generalization to new task instances


###### while learning solely from one to six in-context examples, consistently outperforming baselines with


###### only reasoning or acting across different domains. We also show in Section 3 additional benefits


###### when finetuning is enabled, and in Section 4 how ReAct performance is robust to prompt selections.


###### D) Human aligned and controllable: ReAct promises an interpretable sequential decision making


###### and reasoning process where humans can easily inspect reasoning and factual correctness. Moreover,


###### humans can also control or correct the agent behavior on the go by thought editing, as shown in


###### Figure 5 in Section 4.


###### 3


###### KNOWLEDGE-INTENSIVE REASONING TASKS


###### We begin with knowledge-intensive reasoning tasks like multi-hop question answering and fact


###### verification. As shown in Figure 1(1d), by interacting with a Wikipedia API, ReAct is able to


###### retrieve information to support reasoning, while also use reasoning to target what to retrieve next,


###### demonstrating a synergy of reasoning and acting.


###### 3.1


###### SETUP


###### Domains


###### We consider two datasets challenging knowledge retrieval and reasoning: (1) Hot-


###### PotQA (Yang et al., 2018), a multi-hop question answering benchmark that requires reasoning


###### over two or more Wikipedia passages, and (2) FEVER (Thorne et al., 2018), a fact verification


###### benchmark where each claim is annotated SUPPORTS, REFUTES, or NOT ENOUGH INFO, based


###### on if there exists a Wikipedia passage to verify the claim. In this work, we operate in a question-only


###### setup for both tasks, where models only receive the question/claim as input without access to support


###### paragraphs, and have to rely on their internal knowledge or retrieve knowledge via interacting with


###### an external environment to support reasoning.


###### Action Space


###### We design a simple Wikipedia web API with three types of actions to support


###### interactive information retrieval: (1) search[entity], which returns the first 5 sentences from


###### the corresponding entity wiki page if it exists, or else suggests top-5 similar entities from the


###### Wikipedia search engine, (2) lookup[string], which would return the next sentence in the page


###### containing string, simulating Ctrl+F functionality on the browser. (3) finish[answer], which


###### would finish the current task with answer. We note that this action space mostly can only retrieve a


###### small part of a passage based on exact passage name, which is significantly weaker than state-of-the-


###### art lexical or neural retrievers. The purpose is to simulate how humans would interact with Wikipedia,


###### and force models to retrieve via explicit reasoning in language.


###### 3.2


###### METHODS


###### ReAct Prompting


###### For HotpotQA and Fever, we randomly select 6 and 3 cases2 from the training


###### set and manually compose ReAct-format trajectories to use as few-shot exemplars in the prompts.


###### Similar to Figure 1(d), each trajectory consists of multiple thought-action-observation steps (i.e. dense


###### thought), where free-form thoughts are used for various purposes. Specifically, we use a combination


###### of thoughts that decompose questions (“I need to search x, find y, then find z”), extract information


###### from Wikipedia observations (“x was started in 1844”, “The paragraph does not tell x”), perform


###### commonsense (“x is not y, so z must instead be...”) or arithmetic reasoning (“1844 < 1989”), guide


###### 2We find more examples do not improve performance.


###### 4


---
### 【第 5 页】


###### Published as a conference paper at ICLR 2023


###### Prompt Methoda


###### HotpotQA


###### Fever


###### (EM)


###### (Acc)


###### Standard


###### 28.7


###### 57.1


###### CoT (Wei et al., 2022)


###### 29.4


###### 56.3


###### CoT-SC (Wang et al., 2022a)


###### 33.4


###### 60.4


###### Act


###### 25.7


###### 58.9


###### ReAct


###### 27.4


###### 60.9


###### CoT-SC →ReAct


###### 34.2


###### 64.6


###### ReAct→CoT-SC


###### 35.1


###### 62.0


###### Supervised SoTAb


###### 67.5


###### 89.5


###### Table 1: PaLM-540B prompting results on


###### HotpotQA and Fever.

aHotpotQA EM is 27.1, 28.9, 33.8 for Standard, CoT,
CoT-SC in Wang et al. (2022b).
b(Zhu et al., 2021; Lewis et al., 2020)
0
5
10
15
20
#CoT-SC trials
26
28
30
32
34
HotpotQA EM
0
5
10
15
20
#CoT-SC trials
47.5
50.0
52.5
55.0
57.5
60.0
62.5
65.0
Fever Acc
Method
CoT-SC -> ReAct
ReAct -> CoT-SC
CoT-SC
ReAct
CoT

###### Figure 2: PaLM-540B prompting results with respect to


###### number of CoT-SC samples used.


###### search reformulation (“maybe I can search/look up x instead”), and synthesize the final answer (“...so


###### the answer is x”). See Appendix C for more details.


###### Baselines


###### We systematically ablate ReAct trajectories to build prompts for multiple baselines (with


###### formats as Figure 1(1a-1c)): (a) Standard prompting (Standard), which removes all thoughts,


###### actions, observations in ReAct trajectories. (b) Chain-of-thought prompting (CoT) (Wei et al.,


###### 2022), which removes actions and observations and serve as a reasoning-only baseline. We also


###### build a self-consistency baseline (CoT-SC) (Wang et al., 2022a;b) by sampling 21 CoT trajectories


###### with decoding temperature 0.7 during inference and adopting the majority answer, which is found to


###### consistently boost performance over CoT. (c) Acting-only prompt (Act), which removes thoughts


###### in ReAct trajectories, loosely resembling how WebGPT (Nakano et al., 2021) interacts with the


###### Internet to answer questions, though it operates on a different task and action space, and uses imitation


###### and reinforcement learning instead of prompting.


###### Combining Internal and External Knowledge


###### As will be detail in Section 3.3, we observe that


###### the problem solving process demonstrated by ReAct is more factual and grounded, whereas CoT


###### is more accurate in formulating reasoning structure but can easily suffer from hallucinated facts


###### or thoughts. We therefore propose to incorporate ReAct and CoT-SC, and let the model decide


###### when to switch to the other method based on the following heuristics: A) ReAct →CoT-SC: when


###### ReAct fails to return an answer within given steps, back off to CoT-SC. We set 7 and 5 steps for


###### HotpotQA and FEVER respectively as we find more steps will not improve ReAct performance3.


###### B) CoT-SC →ReAct: when the majority answer among n CoT-SC samples occurs less than n/2


###### times (i.e. internal knowledge might not support the task confidently), back off to ReAct.


###### Finetuning


###### Due to the challenge of manually annotating reasoning traces and actions at scale,


###### we consider a bootstraping approach similar to Zelikman et al. (2022), using 3,000 trajectories


###### with correct answers generated by ReAct (also for other baselines) to finetune smaller language


###### models (PaLM-8/62B) to decode trajectories (all thoughts, actions, observations) conditioned on


###### input questions/claims. More details are in Appendix B.1.


###### 3.3


###### RESULTS AND OBSERVATIONS


###### ReAct outperforms Act consistently


###### Table 1 shows HotpotQA and Fever results using PaLM-


###### 540B as the base model with different prompting methods. We note that ReAct is better than Act


###### on both tasks, demonstrating the value of reasoning to guide acting, especially for synthesizing the


###### final answer, as shown in Figure 1 (1c-d). Fine-tuning results 3 also confirm the benefit of reasoning


###### traces for more informed acting.


###### 3Of all trajectories with correct final answers, those with 7 steps on HotpotQA and 5 steps on FEVER only


###### take up 0.84% and 1.33% respectively.


###### 5


---
### 【第 6 页】


###### Published as a conference paper at ICLR 2023

Type
Definition
ReAct
CoT
Success
True positive
Correct reasoning trace and facts
94%
86%
False positive
Hallucinated reasoning trace or facts
6%
14%
Failure
Reasoning error
Wrong reasoning trace (including failing to recover from repetitive steps)
47%
16%
Search result error
Search return empty or does not contain useful information
23%
-
Hallucination
Hallucinated reasoning trace or facts
0%
56%
Label ambiguity
Right prediction but did not match the label precisely
29%
28%

###### Table 2: Types of success and failure modes of ReAct and CoT on HotpotQA, as well as their


###### percentages in randomly selected examples studied by human.


###### ReAct vs. CoT


###### On the other hand, ReAct outperforms CoT on Fever (60.9 vs. 56.3) and slightly


###### lags behind CoT on HotpotQA (27.4 vs. 29.4). Fever claims for SUPPORTS/REFUTES might only


###### differ by a slight amount (see Appendix D.1), so acting to retrieve accurate and up-to-date knowledge


###### is vital. To better understand the behavioral difference between ReAct and CoT on HotpotQA, we


###### randomly sampled 50 trajectories with correct and incorrect answers (judged by EM) from ReAct


###### and CoT respectively (thus 200 examples in total), and manually labeled their success and failure


###### modes in Table 2. Some key observations are as follows:


###### A) Hallucination is a serious problem for CoT, resulting in much higher false positive rate than


###### ReAct (14% vs. 6%) in success mode, and make up its major failure mode (56%). In contrast, the


###### problem solving trajectory of ReActis more grounded, fact-driven, and trustworthy, thanks to the


###### access of an external knowledge base.


###### B) While interleaving reasoning, action and observation steps improves ReAct’s grounded-


###### ness and trustworthiness, such a structural constraint also reduces its flexibility in formulating


###### reasoning steps, leading to more reasoning error rate than CoT. we note that there is one frequent


###### error pattern specific to ReAct, in which the model repetitively generates the previous thoughts and


###### actions, and we categorize it as part of “reasoning error” as the model fails to reason about what the


###### proper next action to take and jump out of the loop4.


###### C) For ReAct, successfully retrieving informative knowledge via search is critical. Non-


###### informative search, which counts for 23% of the error cases, derails the model reasoning and gives


###### it a hard time to recover and reformulate thoughts. This is perhaps an expected trade-off between


###### factuality and flexibility, which motivates our proposed strategies of combining two methods.


###### We provide examples for each success and failure modes in Appendix E.1. We also find some


###### HotpotQA questions may contain outdated answer labels, see Figure 4 for example.


###### ReAct + CoT-SC perform best for prompting LLMs


###### Also shown in Table 1, the best prompting


###### method on HotpotQA and Fever are ReAct →CoT-SC and CoT-SC →ReAct respectively.


###### Furthermore, Figure 2 shows how different methods perform with respect to the number of CoT-SC


###### samples used. While two ReAct + CoT-SC methods are advantageous at one task each, they both


###### significantly and consistently outperform CoT-SC across different number of samples, reaching


###### CoT-SC performance with 21 samples using merely 3-5 samples. These results indicate the value of


###### properly combining model internal knowledge and external knowledge for reasoning tasks.


###### ReAct performs best for fine-tuning


###### Figure 3 shows the scaling effect of prompting/finetuning


###### four methods (Standard, CoT, Act, ReAct) on HotpotQA. With PaLM-8/62B, prompting ReAct


###### performs worst among four methods due to the difficulty to learn both reasoning and acting from


###### in-context examples. However, when finetuned with just 3,000 examples, ReAct becomes the best


###### method among the four, with PaLM-8B finetuned ReAct outperforming all PaLM-62B prompting


###### methods, and PaLM-62B finetuned ReAct outperforming all 540B prompting methods. In contrast,


###### finetuning Standard or CoT is significantly worse than finetuning ReAct or Act for both PaLM-


###### 8/62B, as the former essentially teaches models to memorize (potentially halluincated) knowledge


###### facts, and the latter teaches models how to (reason and) act to access information from Wikipedia, a


###### more generalizable skill for knowledge reasoning. As all prompting methods are still significantly


###### far from domain-specific state-of-the-art approaches (Table 1), we believe finetuning with more


###### human-written data might be a better way to unleash the power of ReAct.


###### 4We suspect that this could be due to the sub-optimal greedy decoding procedure, and future work using


###### better decoding (e.g. beam search) might help address this issue.


###### 6


---
### 【第 7 页】


###### Published as a conference paper at ICLR 2023

8b
62b
540b
size
0
5
10
15
20
25
30
HotpotQA EM
learning = prompt
8b
62b
540b
size
learning = finetune
Method
Standard
CoT
Act
ReAct

###### Figure 3: Scaling results for prompting and finetuning on HotPotQA with ReAct (ours) and baselines.


###### 4


###### DECISION MAKING TASKS


###### We also test ReAct on two language-based interactive decision-making tasks, ALFWorld and


###### WebShop, both of which feature complex environments that require agents to act over long horizons


###### with sparse rewards, warranting the need for reasoning to act and explore effectively.


###### ALFWorld


###### ALFWorld (Shridhar et al., 2020b) (Figure 1(2)) is a synthetic text-based game designed


###### to align with the embodied ALFRED benchmark (Shridhar et al., 2020a). It includes 6 types of


###### tasks in which an agent needs to achieve a high-level goal (e.g. examine paper under desklamp) by


###### navigating and interacting with a simulated household via text actions (e.g. go to coffeetable 1, take


###### paper 2, use desklamp 1). A task instance can have more than 50 locations and take an expert policy


###### more than 50 steps to solve, thus challenging an agent to plan and track subgoals, as well as explore


###### systematically (e.g. check all desks one by one for desklamp). In particular, one challenge built into


###### ALFWorld is the need to determine likely locations for common household items (e.g. desklamps will


###### likely be on desks, shelfs, or dressers), making this environment a good fit for LLMs to exploit their


###### pretrained commonsense knowledge. To prompt ReAct, we randomly annotate three trajectories


###### from the training set for each task type, where each trajectory includes sparse thoughts that (1)


###### decompose the goal, (2) track subgoal completion, (3) determine the next subgoal, and (4) reason via


###### commonsense where to find an object and what to do with it. We show prompts used for ALFWorld


###### in Appendix C.4. Following Shridhar et al. (2020b), we evaluate on 134 unseen evaluation games


###### in a task-specific setup. For robustness, we construct 6 prompts for each task type through each


###### permutation of 2 annotated trajectories from the 3 we annotate. Act prompts are constructed using


###### the same trajectories, but without thoughts — since task instances are randomly chosen from the


###### training set, it favors neither ReAct nor Act and provides a fair and controlled comparison to test the


###### importance of sparse thoughts. For baselines, we use BUTLER (Shridhar et al., 2020b), an imitation


###### learning agent trained on 105 expert trajectories for each task type5.


###### WebShop


###### Can ReAct also interact with noisy real-world language environments for practical


###### applications? We investigate WebShop (Yao et al., 2022), a recently proposed online shopping


###### website environment with 1.18M real-world products and 12k human instructions. Unlike ALFWorld,


###### Webshop contains a high variety of structured and unstructured texts (e.g. product titles, descriptions,


###### and options crawled from Amazon), and requires an agent to purchase a product based on a user


###### instruction (e.g. “I am looking for a nightstand with drawers. It should have a nickel finish, and


###### priced lower than $140”) through web interactions (e.g. search “nightstand drawers”, choose buttons


###### such as “color: modern-nickel-white” or “back to search”). This task is evaluated by average score


###### (percentage of desired attributes covered by the chosen product averaged across all episodes) and


###### success rate (percentage of episodes where the chosen product satisfies all requirements) on 500 test


###### instructions. We formulate Act prompts with actions to search, choose product, choose options,


###### and buy, with ReAct prompts additionally reasoning to determine what to explore, when to buy,


###### and what products options are relevant to the instruction. See Table 6 for an example prompt, and


###### Table 10 for model predictions in the Appendix. We compare to an imitation learning (IL) method


###### 5Micheli & Fleuret (2021) finetuned a GPT-2 model on 3553 task instances and achieved a much improved


###### performance than BUTLER, but it is trained on all task types, thus not included as a baseline.


###### 7


---
### 【第 8 页】


###### Published as a conference paper at ICLR 2023


###### Method


###### Pick


###### Clean


###### Heat


###### Cool


###### Look


###### Pick 2


###### All


###### Act (best of 6)


###### 88


###### 42


###### 74


###### 67


###### 72


###### 41


###### 45


###### ReAct (avg)


###### 65


###### 39


###### 83


###### 76


###### 55


###### 24


###### 57


###### ReAct (best of 6)


###### 92


###### 58


###### 96


###### 86


###### 78


###### 41


###### 71


###### ReAct-IM (avg)


###### 55


###### 59


###### 60


###### 55


###### 23


###### 24


###### 48


###### ReAct-IM (best of 6)


###### 62


###### 68


###### 87


###### 57


###### 39


###### 33


###### 53


###### BUTLERg (best of 8)


###### 33


###### 26


###### 70


###### 76


###### 17


###### 12


###### 22


###### BUTLER (best of 8)


###### 46


###### 39


###### 74


###### 100


###### 22


###### 24


###### 37


###### Table 3: AlfWorld task-specific success rates (%). BUTLER and


###### BUTLERg results are from Table 4 of Shridhar et al. (2020b). All


###### methods use greedy decoding, except that BUTLER uses beam search.


###### Method


###### Score


###### SR


###### Act


###### 62.3


###### 30.1


###### ReAct


###### 66.6


###### 40.0


###### IL


###### 59.9


###### 29.1


###### IL+RL


###### 62.4


###### 28.7


###### Human


###### 82.1


###### 59.6


###### Expert


###### Table 4: Score and suc-


###### cess rate (SR) on Web-


###### shop. IL/IL+RL taken


###### from Yao et al. (2022).


###### trained with 1,012 human annotated trajectories, and a imitation + reinforcement learning (IL + RL)


###### method additionally trained with 10,587 training instructions.


###### Results


###### ReAct outperforms Act on both ALFWorld (Table 3) and Webshop (Table 4). On


###### ALFWorld, the best ReAct trial achieves an average success rate of 71%, significantly outperforming


###### the best Act (45%) and BUTLER (37%) trials. In fact, even the worse ReAct trial (48%) beats


###### the best trial of both methods. Moreover, the advantage of ReAct over Act is consistent across


###### six controlled trials, with relative performance gain ranging from 33% to 90% and averaging 62%.


###### Qualitatively, we saw that, without any thoughts at all, Act fails to correctly decompose goals


###### into smaller subgoals, or loses track of the current state of the environment. Example trajectories


###### comparing ReAct and Act can be found in Appendix D.2.1 and Appendix D.2.2.


###### On Webshop, one-shot Act prompting already performs on par with IL and IL+RL methods. With


###### additional sparse reasoning, ReAct achieves significantly better performance, with an absolute 10%


###### improvement over the previous best success rate. By checking examples, we find that ReAct is more


###### likely to identify instruction-relevant products and options by reasoning to bridge the gap between


###### noisy observations and actions (e.g. “For ‘space-saving ottoman bench for living room’, the item


###### has options ‘39x18x18inch’ and ‘blue’ and seems good to buy.”). However, existing methods are


###### still far from the performance of expert humans (Table 4), who perform significantly more product


###### explorations and query re-formulations that are still challenging for prompting-based methods.


###### On the value of internal reasoning vs. external feedback


###### To our knowledge, ReAct is the first


###### demonstration of combined reasoning and action using an LLM applied to an interactive environment


###### within a closed-loop system. Perhaps the closest prior work is Inner Monologue (IM), from Huang


###### et al. (2022b), in which actions from an embodied agent are motivated by an eponymous “inner


###### monologue”. However, IM’s “inner monologue” is limited to observations of the environment


###### state and what needs to be completed by the agent for the goal to be satisfied. In contrast, the


###### reasoning traces in ReAct for decision making is flexible and sparse, allowing diverse reasoning


###### types (see Section 2) to be induced for different tasks.


###### To demonstrate the differences between ReAct and IM, and to highlight the importance of internal


###### reasoning vs. simple reactions to external feedback, we ran an ablation experiment using a thought


###### pattern composed of IM-like dense external feedback. As can be seen in Table 3, ReAct substantially


###### outperforms IM-style prompting (ReAct-IM) (71 vs. 53 overall success rate), with consistent


###### advantages on five out of six tasks. Qualitatively, we observed that ReAct-IM often made mistakes


###### in identifying when subgoals were finished, or what the next subgoal should be, due to a lack of high-


###### level goal decomposition. Additionally, many ReAct-IM trajectories struggled to determine where


###### an item would likely be within the ALFWorld environment, due to a lack of commonsense reasoning.


###### Both shortcomings can be addressed in the ReAct paradigm. More details about ReAct-IM is in


###### Appendix B.2. An example prompt for ReAct-IM can be found in Appendix C.4, and an example


###### trajectory in Appendix D.2.3.


###### 8


---
### 【第 9 页】


###### Published as a conference paper at ICLR 2023


###### 5


###### RELATED WORK


###### Language model for reasoning


###### Perhaps the most well-known work of using LLMs for reasoning


###### is Chain-of-Thought (CoT) (Wei et al., 2022), which reveals the ability of LLMs to formulate their


###### own “thinking procedure” for problem solving. Several follow-up works have since been performed,


###### including least-to-most prompting for solving complicated tasks (Zhou et al., 2022), zero-shot-


###### CoT (Kojima et al., 2022), and reasoning with self-consistency (Wang et al., 2022a). Recently,


###### (Madaan & Yazdanbakhsh, 2022) systematically studied the formulation and structure of CoT, and


###### observed that the presence of symbols, patterns and texts is crucial to the effectiveness of CoT. Other


###### work has also been extended to more sophisticated reasoning architecture beyond simple prompting.


###### For example Selection-Inference (Creswell et al., 2022) divides the reasoning process into two steps


###### of “selection” and “inference”. STaR (Zelikman et al., 2022) bootstraps the reasoning process by


###### finetuning the model on correct rationales generated by the model itself. Faithful reasoning (Creswell


###### & Shanahan, 2022) decomposes multi-step reasoning into three steps, each performed by a dedicated


###### LM respectively. Similar approaches like Scratchpad (Nye et al., 2021), which finetunes a LM on


###### intermediate computation steps, also demonstrate improvement on multi-step computation problems.


###### In contrast to these methods, ReAct performs more than just isolated, fixed reasoning, and integrates


###### model actions and their corresponding observations into a coherent stream of inputs for the model to


###### reason more accurately and tackle tasks beyond reasoning (e.g. interactive decision making).


###### Language model for decision making


###### The strong capability of LLMs has enabled them to perform


###### tasks beyond language generation, and it is becoming more popular to take advantage of LLMs as a


###### policy model for decision making, especially in interactive environments. WebGPT (Nakano et al.,


###### 2021) uses an LM to interact with web browsers, navigate through web pages, and infer answers to


###### complicated questions from ELI5 (Fan et al., 2019). In comparison to ReAct, WebGPT does not


###### explicitly model the thinking and reasoning procedure, instead rely on expensive human feedback for


###### reinforcement learning. In conversation modeling, chatbots like BlenderBot (Shuster et al., 2022b)


###### and Sparrow (Glaese et al., 2022) and task-oriented dialogue systems like SimpleTOD (Hosseini-Asl


###### et al., 2020) also train LMs to make decision about API calls. Unlike ReAct, they do not explicitly


###### consider the reasoning procedure either, and also relies on expensive datasets and human feedback


###### collections for policy learning. In contrast, ReAct learns a policy in a much cheaper way, since the


###### decision making process only requires language description of the reasoning procedure.6


###### LLMS have also been increasingly employed in interactive and embodied environments for planning


###### and decision making. Perhaps most relevant to ReAct in this respect are SayCan (Ahn et al., 2022)


###### and Inner Monologue (Huang et al., 2022b), which use LLMs for robotic action planning and decision


###### making. In SayCan, LLMs were prompted to directly predict possible actions a robot can take, which


###### is then reranked by an affordance model grounded on the visual environments for final prediction.


###### Inner Monologue made further improvements by adding the eponymous “inner monologue", which is


###### implemented as injected feedback from the environment. To our knowledge, Inner Monologue is the


###### first work that demonstrates such a closed-loop system, which ReAct builds on. However, we argue


###### that Inner Monologue does not truly comprise of inner thoughts — this is elaborated in Section 4. We


###### also note that leveraging language as semantically-rich inputs in the process of interactive decision


###### making has been shown to be successful under other settings (Abramson et al., 2020; Karamcheti


###### et al., 2021; Huang et al., 2022a; Li et al., 2022). It is becoming more evident that with the help of


###### LLMs, language as a fundamental cognitive mechanism will play a critical role in interaction and


###### decision making. What is more, progress in LLMs has also inspired the development of versatile and


###### generalist agents like Reed et al. (2022).


###### 6


###### CONCLUSION


###### We have proposed ReAct – a simple yet effective method for synergizing reasoning and acting in


###### large language models. Through a diverse set of experiments on multi-hop question-answering, fact


###### checking, and interactive decision-making tasks, we show that ReAct leads to superior performance


###### with interpretable decision traces. Despite the simplicity of our method, complex tasks with large


###### action spaces require more demonstrations to learn well, which unfortunately can easily go beyond


###### the input length limit of in-context learning. We explore the fine-tuning approach on HotpotQA


###### 6Human feedback can also be incorporated in a complementary manner but we leave it for future work.


###### 9


---
### 【第 10 页】


###### Published as a conference paper at ICLR 2023


###### with initial promising results, but learning from more high-quality human annotations will be the


###### desiderata to further improve the performance. Scaling up ReAct with multi-task training and


###### combining it with complementary paradigms like reinforcement learning could result in stronger


###### agents that further unlock the potential of LLMs for more applications.


###### ACKNOWLEDGMENTS


###### We thank the support and feedback of many people from Google Brain team and Princeton NLP


###### Group. This work was supported in part by the National Science Foundation under Grant No.


###### 2107048. Any opinions, findings, and conclusions or recommendations expressed in this material are


###### those of the author(s) and do not necessarily reflect the views of the National Science Foundation.


###### REPRODUCIBILITY STATEMENT


###### Our main experiments are done on PaLM (Chowdhery et al., 2022), which is not an openly accessible


###### model yet. To increase reproducibility, we have included all used prompts in Appendix C, additional


###### experiments using GPT-3 (Brown et al., 2020) in Appendix A.1, and associated GPT-3 ReAct


###### prompting code at https://anonymous.4open.science/r/ReAct-2268/.


###### ETHICS STATEMENT


###### ReAct prompts large language models to generate more human interpretable, diagnosable, and


###### controllable task-solving trajectories than previous methods. However, hooking up a large language


###### model with an action space to interact with external environments (e.g. the web, physical environ-


###### ments) has potential dangers, e.g. looking up inappropriate or private information, or taking harmful


###### actions in an environment. Our experiments minimize such risks by limiting the interactions to


###### specific websites (Wikipedia or WebShop) that are free of private information, without any dangerous


###### actions in the action space design (i.e. models cannot really buy products on WebShop the research


###### benchmark, or edit Wikipedia). We believe researchers should be aware of such risks before designing


###### more extensive experiments in the future.


###### REFERENCES


###### Josh Abramson, Arun Ahuja, Iain Barr, Arthur Brussee, Federico Carnevale, Mary Cassin, Rachita


###### Chhaparia, Stephen Clark, Bogdan Damoc, Andrew Dudzik, Petko Georgiev, Aurelia Guy, Tim


###### Harley, Felix Hill, Alden Hung, Zachary Kenton, Jessica Landon, Timothy Lillicrap, Kory Mathew-


###### son, Soˇna Mokrá, Alistair Muldal, Adam Santoro, Nikolay Savinov, Vikrant Varma, Greg Wayne,


###### Duncan Williams, Nathaniel Wong, Chen Yan, and Rui Zhu. Imitating interactive intelligence,


###### 2020. URL https://arxiv.org/abs/2012.05672.


###### Michael Ahn, Anthony Brohan, Noah Brown, Yevgen Chebotar, Omar Cortes, Byron David, Chelsea


###### Finn, Chuyuan Fu, Keerthana Gopalakrishnan, Karol Hausman, Alex Herzog, Daniel Ho, Jasmine


###### Hsu, Julian Ibarz, Brian Ichter, Alex Irpan, Eric Jang, Rosario Jauregui Ruano, Kyle Jeffrey, Sally


###### Jesmonth, Nikhil J Joshi, Ryan Julian, Dmitry Kalashnikov, Yuheng Kuang, Kuang-Huei Lee,


###### Sergey Levine, Yao Lu, Linda Luu, Carolina Parada, Peter Pastor, Jornell Quiambao, Kanishka


###### Rao, Jarek Rettinghouse, Diego Reyes, Pierre Sermanet, Nicolas Sievers, Clayton Tan, Alexander


###### Toshev, Vincent Vanhoucke, Fei Xia, Ted Xiao, Peng Xu, Sichun Xu, Mengyuan Yan, and


###### Andy Zeng. Do as i can, not as i say: Grounding language in robotic affordances, 2022. URL


###### https://arxiv.org/abs/2204.01691.


###### Ben Alderson-Day and Charles Fernyhough.


###### Inner speech: development, cognitive functions,


###### phenomenology, and neurobiology. Psychological bulletin, 141(5):931, 2015.


###### Alan Baddeley. Working memory. Science, 255(5044):556–559, 1992.


###### Tom Brown, Benjamin Mann, Nick Ryder, Melanie Subbiah, Jared D Kaplan, Prafulla Dhariwal,


###### Arvind Neelakantan, Pranav Shyam, Girish Sastry, Amanda Askell, et al. Language models are


###### few-shot learners. Advances in neural information processing systems, 33:1877–1901, 2020.


###### 10


---
### 【第 11 页】


###### Published as a conference paper at ICLR 2023


###### Aakanksha Chowdhery, Sharan Narang, Jacob Devlin, Maarten Bosma, Gaurav Mishra, Adam


###### Roberts, Paul Barham, Hyung Won Chung, Charles Sutton, Sebastian Gehrmann, et al. Palm:


###### Scaling language modeling with pathways. arXiv preprint arXiv:2204.02311, 2022.


###### Antonia Creswell and Murray Shanahan. Faithful reasoning using large language models, 2022. URL


###### https://arxiv.org/abs/2208.14271.


###### Antonia Creswell, Murray Shanahan, and Irina Higgins. Selection-inference: Exploiting large


###### language models for interpretable logical reasoning, 2022. URL https://arxiv.org/abs/


###### 2205.09712.


###### Angela Fan, Yacine Jernite, Ethan Perez, David Grangier, Jason Weston, and Michael Auli. ELI5:


###### Long form question answering. In Proceedings of the 57th Annual Meeting of the Association


###### for Computational Linguistics, pp. 3558–3567, Florence, Italy, July 2019. Association for Com-


###### putational Linguistics. doi: 10.18653/v1/P19-1346. URL https://aclanthology.org/


###### P19-1346.


###### Charles Fernyhough. Vygotsky, luria, and the social brain. Self and social regulation: Social


###### interaction and the development of social understanding and executive functions, pp. 56–79, 2010.


###### Amelia Glaese, Nat McAleese, Maja Trebacz, John Aslanides, Vlad Firoiu, Timo Ewalds, Mari-


###### beth Rauh, Laura Weidinger, Martin Chadwick, Phoebe Thacker, Lucy Campbell-Gillingham,


###### Jonathan Uesato, Po-Sen Huang, Ramona Comanescu, Fan Yang, Abigail See, Sumanth


###### Dathathri, Rory Greig, Charlie Chen, Doug Fritz, Jaume Sanchez Elias, Richard Green,


###### Soˇna Mokrá, Nicholas Fernando, Boxi Wu, Rachel Foley, Susannah Young, Iason Gabriel,


###### William Isaac, John Mellor, Demis Hassabis, Koray Kavukcuoglu, Lisa Anne Hendricks, and


###### Geoffrey Irving.


###### Improving alignment of dialogue agents via targeted human judgements,


###### 2022.


###### URL https://storage.googleapis.com/deepmind-media/DeepMind.


###### com/Authors-Notes/sparrow/sparrow-final.pdf.


###### Ehsan Hosseini-Asl, Bryan McCann, Chien-Sheng Wu, Semih Yavuz, and Richard Socher. A simple


###### language model for task-oriented dialogue. Advances in Neural Information Processing Systems,


###### 33:20179–20191, 2020.


###### Wenlong Huang, Pieter Abbeel, Deepak Pathak, and Igor Mordatch. Language models as zero-shot


###### planners: Extracting actionable knowledge for embodied agents. arXiv preprint arXiv:2201.07207,


###### 2022a.


###### Wenlong Huang, Fei Xia, Ted Xiao, Harris Chan, Jacky Liang, Pete Florence, Andy Zeng, Jonathan


###### Tompson, Igor Mordatch, Yevgen Chebotar, et al. Inner monologue: Embodied reasoning through


###### planning with language models. arXiv preprint arXiv:2207.05608, 2022b.


###### Siddharth Karamcheti, Megha Srivastava, Percy Liang, and Dorsa Sadigh. Lila: Language-informed


###### latent actions. In CoRL, pp. 1379–1390, 2021. URL https://proceedings.mlr.press/


###### v164/karamcheti22a.html.


###### Takeshi Kojima, Shixiang Shane Gu, Machel Reid, Yutaka Matsuo, and Yusuke Iwasawa. Large


###### language models are zero-shot reasoners. arXiv preprint arXiv:2205.11916, 2022.


###### Angeliki Lazaridou, Elena Gribovskaya, Wojciech Stokowiec, and Nikolai Grigorev. Internet-


###### augmented language models through few-shot prompting for open-domain question answering.


###### arXiv preprint arXiv:2203.05115, 2022.


###### Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal,


###### Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, et al. Retrieval-augmented genera-


###### tion for knowledge-intensive nlp tasks. Advances in Neural Information Processing Systems, 33:


###### 9459–9474, 2020.


###### Shuang Li, Xavier Puig, Chris Paxton, Yilun Du, Clinton Wang, Linxi Fan, Tao Chen, De-An


###### Huang, Ekin Akyürek, Anima Anandkumar, Jacob Andreas, Igor Mordatch, Antonio Torralba,


###### and Yuke Zhu. Pre-trained language models for interactive decision-making, 2022. URL https:


###### //arxiv.org/abs/2202.01771.


###### 11


---
### 【第 12 页】


###### Published as a conference paper at ICLR 2023


###### Aleksandr Romanovich Luria. Ls vygotsky and the problem of localization of functions. Neuropsy-


###### chologia, 3(4):387–392, 1965.


###### Aman Madaan and Amir Yazdanbakhsh. Text and patterns: For effective chain of thought, it takes


###### two to tango, 2022. URL https://arxiv.org/abs/2209.07686.


###### Vincent Micheli and François Fleuret. Language models are few-shot butlers. arXiv preprint


###### arXiv:2104.07972, 2021.


###### Reiichiro Nakano, Jacob Hilton, Suchir Balaji, Jeff Wu, Long Ouyang, Christina Kim, Christopher


###### Hesse, Shantanu Jain, Vineet Kosaraju, William Saunders, Xu Jiang, Karl Cobbe, Tyna Eloundou,


###### Gretchen Krueger, Kevin Button, Matthew Knight, Benjamin Chess, and John Schulman. Webgpt:


###### Browser-assisted question-answering with human feedback, 2021. URL https://arxiv.


###### org/abs/2112.09332.


###### Maxwell Nye, Anders Johan Andreassen, Guy Gur-Ari, Henryk Michalewski, Jacob Austin, David


###### Bieber, David Dohan, Aitor Lewkowycz, Maarten Bosma, David Luan, Charles Sutton, and


###### Augustus Odena. Show your work: Scratchpads for intermediate computation with language


###### models, 2021. URL https://arxiv.org/abs/2112.00114.


###### Scott Reed, Konrad Zolna, Emilio Parisotto, Sergio Gomez Colmenarejo, Alexander Novikov,


###### Gabriel Barth-Maron, Mai Gimenez, Yury Sulsky, Jackie Kay, Jost Tobias Springenberg, Tom


###### Eccles, Jake Bruce, Ali Razavi, Ashley Edwards, Nicolas Heess, Yutian Chen, Raia Hadsell,


###### Oriol Vinyals, Mahyar Bordbar, and Nando de Freitas. A generalist agent, 2022. URL https:


###### //arxiv.org/abs/2205.06175.


###### Mohit Shridhar, Jesse Thomason, Daniel Gordon, Yonatan Bisk, Winson Han, Roozbeh Mottaghi,


###### Luke Zettlemoyer, and Dieter Fox. Alfred: A benchmark for interpreting grounded instructions


###### for everyday tasks. In Proceedings of the IEEE/CVF conference on computer vision and pattern


###### recognition, pp. 10740–10749, 2020a.


###### Mohit Shridhar, Xingdi Yuan, Marc-Alexandre Côté, Yonatan Bisk, Adam Trischler, and Matthew


###### Hausknecht. Alfworld: Aligning text and embodied environments for interactive learning. arXiv


###### preprint arXiv:2010.03768, 2020b.


###### Kurt Shuster, Mojtaba Komeili, Leonard Adolphs, Stephen Roller, Arthur Szlam, and Jason Weston.


###### Language models that seek for knowledge: Modular search & generation for dialogue and prompt


###### completion. arXiv preprint arXiv:2203.13224, 2022a.


###### Kurt Shuster, Jing Xu, Mojtaba Komeili, Da Ju, Eric Michael Smith, Stephen Roller, Megan Ung,


###### Moya Chen, Kushal Arora, Joshua Lane, Morteza Behrooz, William Ngan, Spencer Poff, Naman


###### Goyal, Arthur Szlam, Y-Lan Boureau, Melanie Kambadur, and Jason Weston. Blenderbot 3:


###### a deployed conversational agent that continually learns to responsibly engage, 2022b. URL


###### https://arxiv.org/abs/2208.03188.


###### James Thorne, Andreas Vlachos, Christos Christodoulopoulos, and Arpit Mittal. Fever: a large-scale


###### dataset for fact extraction and verification. arXiv preprint arXiv:1803.05355, 2018.


###### Lev S Vygotsky. Thinking and speech. The collected works of LS Vygotsky, 1:39–285, 1987.


###### Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le, Ed Chi, Sharan Narang, Aakanksha Chowdh-


###### ery, and Denny Zhou. Self-consistency improves chain of thought reasoning in language models,


###### 2022a. URL https://arxiv.org/abs/2203.11171.


###### Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le, Ed Chi, and Denny Zhou. Rationale-augmented


###### ensembles in language models. arXiv preprint arXiv:2207.00747, 2022b.


###### Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Ed Chi, Quoc Le, and Denny


###### Zhou. Chain of thought prompting elicits reasoning in large language models. arXiv preprint


###### arXiv:2201.11903, 2022.


###### Zhilin Yang, Peng Qi, Saizheng Zhang, Yoshua Bengio, William W Cohen, Ruslan Salakhutdinov,


###### and Christopher D Manning. Hotpotqa: A dataset for diverse, explainable multi-hop question


###### answering. arXiv preprint arXiv:1809.09600, 2018.


###### 12


---
### 【第 13 页】


###### Published as a conference paper at ICLR 2023


###### Shunyu Yao, Rohan Rao, Matthew Hausknecht, and Karthik Narasimhan. Keep CALM and explore:


###### Language models for action generation in text-based games. In Proceedings of the 2020 Conference


###### on Empirical Methods in Natural Language Processing (EMNLP), pp. 8736–8754, Online, Novem-


###### ber 2020. Association for Computational Linguistics. doi: 10.18653/v1/2020.emnlp-main.704.


###### URL https://aclanthology.org/2020.emnlp-main.704.


###### Shunyu Yao, Howard Chen, John Yang, and Karthik Narasimhan. Webshop: Towards scalable


###### real-world web interaction with grounded language agents. arXiv preprint arXiv:2207.01206,


###### 2022.


###### Eric Zelikman, Yuhuai Wu, Jesse Mu, and Noah D. Goodman. Star: Bootstrapping reasoning with


###### reasoning, 2022. URL https://arxiv.org/abs/2203.14465.


###### Denny Zhou, Nathanael Schärli, Le Hou, Jason Wei, Nathan Scales, Xuezhi Wang, Dale Schuurmans,


###### Olivier Bousquet, Quoc Le, and Ed Chi. Least-to-most prompting enables complex reasoning in


###### large language models, 2022. URL https://arxiv.org/abs/2205.10625.


###### Yunchang Zhu, Liang Pang, Yanyan Lan, Huawei Shen, and Xueqi Cheng. Adaptive information


###### seeking for open-domain question answering. arXiv preprint arXiv:2109.06747, 2021.


###### 13


---
### 【第 14 页】


###### Published as a conference paper at ICLR 2023


###### A


###### ADDITIONAL RESULTS


###### A.1


###### GPT-3 EXPERIMENTS


###### PaLM-540B


###### GPT-3


###### HotpotQA (exact match)


###### 29.4


###### 30.8


###### ALFWorld (success rate %)


###### 70.9


###### 78.4


###### Table 5: ReAct prompting results using PaLM-540B vs. GPT-3 (text-davinci-002, greedy decoding).


###### On HotpotQA, we randomly sample a subset of 500 validation questions. On ALFWorld, we use all


###### 134 unseen validation task instances, and use the best prompt set according to PaLM-540B.


###### We run additional GPT-3 (Brown et al., 2020) experiments to confirm ReAct prompting performance


###### is general across different large language models. As shown in Table 5, GPT-3 (text-davinci-002,


###### greedy decoding) consistently outperforms PaLM-540B on HotpotQA and ALFWorld, possibly


###### because it is finetuned with human instruction following. This indicates ReAct prompting is effective


###### across different large language models on different tasks. The code for these experiments are at


###### https://react-lm.github.io/.


###### A.2


###### REACT OBTAINS UP-TO-DATE KNOWLEDGE ON HOTPOTQA

�������������
�������������
����������������������
��������������������������
���������������������������
����������������������
�����������������������
��������������������������
���������������������������
��������������������
�������������
��������������
��������������������������������
�����������������������������
�������������������������������
�����������������������
����������������������
���������������������������������
��������������
����������������������
���������������������������������
���������
������������������������������
�����������
������������������������������
������������������
����������������������
�������������������������
����������������������������������������������������������
�
���������������������������������������������������������
�
����������
��������������������������������������������
����������������������������������������������������
�
������������������������������
����������������������������������������������������������
�
�����������
�����������������������������������������
������������������������������������������������������������
��������������������������������������
������������������������������������������������������
�����������������������������������������������������
�
���������������������������������������������������������
�
����������������������
�����������������������������������������������
�����������������������������������������������������������
����������������
�����������������������������������������������������������
�
���������������������������������������
��������������������

###### �

���������������������������������������������������������
�
����������������������������������
���������������������
��������������
���������
�����������

###### Figure 4: Another example HotpotQA question, where the original label is outdated. Only ReAct is


###### able to obtain the up-to-date answer thanks to real-world web interaction plus reasoning.


###### During trajectory inspection, we also find that sometimes ReAct does not agree with dataset labels as


###### the labels themselves could be outdated. For example, as shown in Figure 4, the question asks about


###### the size of a hotel, which increased from the HotpotQA construction time. While Standard and CoT


###### give wrong answers due to hallucination, Act fails despite the access of real-world web interaction,


###### due to a lack of reasoning to guide how to interact with the Internet for QA. Only ReAct is able to


###### retrieve up-to-date information from the Internet and provide a reasonable answer. Therefore, better


###### incorporation of reasoning abilities might benefit recent Internet-augmented language models (Nakano


###### et al., 2021; Lazaridou et al., 2022; Shuster et al., 2022a) for up-to-date task solving.


###### A.3


###### HUMAN-IN-THE-LOOP BEHAVIOR CORRECTION ON ALFWORLD


###### We also explore human-in-the-loop interaction with ReAct, to allow a human to inspect and edit


###### ReAct’s reasoning traces. Figure 5 shows that by simply removing a hallucinating sentence in Act


###### 17 and adding some hints in Act 23, ReAct can be made to change its behavior drastically to align


###### with these human thought edits and succeed in the task. From a human perspective, solving such a


###### task becomes significantly easier, from typing tens of actions to only editing a couple of thoughts,


###### which enables new forms of human-machine collaboration. We note that such a policy edit on-the-go


###### 14


---
### 【第 15 页】


###### Published as a conference paper at ICLR 2023

����������
������
���������������������������������������������������������������
�
���������������������������������
�����������������������������������������������������������������
�
��������������������������������������������������������������
��
��������������������������������������
�����������������������������������������������������
�
������
������������������������������������
�������������������������������������������������
�����������������������������������������������������������������
�
�����������������������������������������������������������
��
�����������������������
�������������������������������������������������������
�
���������������������������������������������������������������
�
������������
��������������������������������������
������������������������
������������������������������
������
���������������������������������������������������������������������
�
���������������������������
���������������������������������������������������������������������������
��
���������������������������������������������������
�
��������������������������������������
�����������������������������������������������������
�
������
������������������������������������
�������������������������������������������������
�������������������������������������������������������������������������
�
�������������������������������������������������������������������
�
���������������������������������������������������������������
��
������������������������
��������������������������������������������������������������������������
�
�������������������������
������������������������������������������������������������������������
����
���������������������������������������
������������������������������������������������������
�
��������������������������������������������������������������������������
��������������
��������������������
��������������������������������������������������������������������������
�
��������
�����������������������������������
������������������������������������������������

###### �

������������������������������������������������������������
�
�������������������������������������������������������������
�
�������������������������������������������������������������
�
����������������������������������������������
�
������������������������������������������
��������

###### Figure 5: A human-in-the-loop behavior correction example with ReAct in AlfWorld. (a) ReAct


###### trajectory fails due to a hallucinating thought (Act 17). (b) By a human simply editing two thoughts


###### (Act 17, 23), the ReAct trajectory produces desirable reasoning traces and actions and succeeds.


###### is difficult for Act and previous RL methods, as a human cannot change the model parameters, and


###### changing a few actions might not edit the rest of the model behavior. This paradigm is also more than


###### human dialogue to update the goal or subgoal as in Huang et al. (2022b) — while editing ReAct


###### thoughts can do these, it can also modify the model’s internal belief, reasoning styles, or anything the


###### flexible thought space supports, for better task solving. We believe this is an exciting direction for


###### human alignment and leave more systematic study as future work.


###### B


###### EXPERIMENT DETAILS


###### B.1


###### HOTPOTQA FINETUNING DETAILS


###### For all finetuning we use a batch size of 64. On PaLM-8B, we finetune ReAct and Act methods


###### for 4, 000 steps and Standard and CoT methods for 2, 000 steps. On PaLM-62B, we finetune


###### ReAct and Act methods for 4, 000 steps and Standard and CoT methods for 1, 000 steps. We


###### find ReAct and Act methods generally benefit from more training steps (and more training data),


###### while Standard and CoT methods degrade soon after finetuning.


###### B.2


###### ALFWORLD IM-STYLE DETAILS


###### For the IM-style ablation, the same expert trajectories used in ReAct are reannotated with dense


###### external feedback thoughts within these trajectories, that limit ReAct-IM to only think about (1)


###### decomposing the current goal and (2) the current subgoal that needs to be completed. In particular,


###### ReAct-IM lacks thoughts that (1) determine when a subgoal is completed (2) determine what the


###### next subgoal should be (3) inducing the LLM to refer to its internal pretraining knowledge to identify


###### where items can be within the environment.


###### 15


---
### 【第 16 页】


###### Published as a conference paper at ICLR 2023


###### C


###### PROMPTS


###### C.1


###### HOTPOTQA

Hotpot QA Prompts
Original
Question
What is the elevation range for the area that the eastern sector of the
Colorado orogeny extends into?
Answer
1,800 to 7,000 ft
Question
Musician and satirist Allie Goertz wrote a song about the "The Simpsons"
character Milhouse, who Matt Groening named after who?
Answer
Richard Nixon
Question
Which documentary is about Finnish rock groups, Adam Clayton Powell or The
Saimaa Gesture?
Answer
The Saimaa Gesture
Question
What profession does Nicholas Ray and Elia Kazan have in common?
Answer
director, screenwriter, actor
Question
Which magazine was started first Arthur’s Magazine or First for Women?
Answer
Arthur’s Magazine
Question
Were Pavel Urysohn and Leonid Levin known for the same type of work?
Answer
Yes
Act
Question
What is the elevation range for the area that the eastern sector of the
Colorado orogeny extends into?
Action 1
Search[Colorado orogeny]
Observation 1
The Colorado orogeny was an episode of mountain building (an orogeny) in
Colorado and surrounding areas.
Action 2
Lookup[eastern sector]
Observation 2
(Result 1 / 1) The eastern sector extends into the High Plains and is called
the Central Plains orogeny.
Action 3
Search[High Plains]
Observation 3
High Plains refers to one of two distinct land regions:
Action 4
Search[High Plains (United States)]
Observation 4
The High Plains are a subregion of the Great Plains.
From east to west, the
High Plains rise in elevation from around 1,800 to 7,000 ft (550 to 2,130
m).[3]
Action 5
Finish[1,800 to 7,000 ft]
Question
Musician and satirist Allie Goertz wrote a song about the "The Simpsons"
character Milhouse, who Matt Groening named after who?
Action 1
Search[Milhouse]
Observation 1
Milhouse Mussolini Van Houten is a recurring character in the Fox animated
television series The Simpsons voiced by Pamela Hayden and created by Matt
Groening.
Action 2
Lookup[named after]
Observation 2
(Result 1 / 1) Milhouse was named after U.S. president Richard Nixon, whose
middle name was Milhous.
Action 3
Finish[Richard Nixon]
Question
Which documentary is about Finnish rock groups, Adam Clayton Powell or The
Saimaa Gesture?
Action 1
Search[Adam Clayton Powell]
Observation 1
Could not find [Adam Clayton Powell].
Similar:
[’Adam Clayton Powell
III’, ’Seventh Avenue (Manhattan)’, ’Adam Clayton Powell Jr.
State Office
Building’, ’Isabel Washington Powell’, ’Adam Powell’, ’Adam Clayton Powell
(film)’, ’Giancarlo Esposito’].
Action 2
Search[Adam Clayton Powell (film)]
Observation 2
Adam Clayton Powell is a 1989 American documentary film directed by
Richard Kilberg.
The film is about the rise and fall of influential
African-American politician Adam Clayton Powell Jr.[3][4] It was later aired
as part of the PBS series The American Experience.
Action 3
Finish[The Saimaa Gesture]
Question
What profession does Nicholas Ray and Elia Kazan have in common?
Action 1
Search[Nicholas Ray]
Observation 1
Nicholas Ray (born Raymond Nicholas Kienzle Jr., August 7, 1911 - June 16,
1979) was an American film director, screenwriter, and actor best known for
the 1955 film Rebel Without a Cause.
Action 2
Search[Elia Kazan]
Observation 2
Elia Kazan was an American film and theatre director, producer, screenwriter
and actor.
Continued on next page

###### 16


---
### 【第 17 页】


###### Published as a conference paper at ICLR 2023

Hotpot QA Prompts – Continued from previous page
Action 3
Finish[director, screenwriter, actor]
Question
Which magazine was started first Arthur’s Magazine or First for Women?
Action 1
Search[Arthur’s Magazine]
Observation 1
Arthur’s Magazine (1844-1846) was an American literary periodical published
in Philadelphia in the 19th century.
Action 2
Search[First for Women]
Observation 2
First for Women is a woman’s magazine published by Bauer Media Group in the
USA.[1] The magazine was started in 1989.
Action 3
Finish[Arthur’s Magazine]
Question
Were Pavel Urysohn and Leonid Levin known for the same type of work?
Action 1
Search[Pavel Urysohn]
Observation 1
Pavel Samuilovich Urysohn (February 3, 1898 - August 17, 1924) was a Soviet
mathematician who is best known for his contributions in dimension theory.
Action 2
Search[Leonid Levin]
Observation 2
Leonid Anatolievich Levin is a Soviet-American mathematician and computer
scientist.
Action 3
Finish[yes]
CoT
Question
What is the elevation range for the area that the eastern sector of the
Colorado orogeny extends into?
Thought
Let’s think step by step.
The eastern sector of Colorado orogeny extends
into the High Plains.
High Plains rise in elevation from around 1,800 to
7,000 ft, so the answer is 1,800 to 7,000 ft.
Answer
1,800 to 7,000 ft
Question
Musician and satirist Allie Goertz wrote a song about the "The Simpsons"
character Milhouse, who Matt Groening named after who?
Thought
Let’s think step by step.
Milhouse was named after U.S. president Richard
Nixon, so the answer is Richard Nixon.
Answer
Richard Nixon
Question
Which documentary is about Finnish rock groups, Adam Clayton Powell or The
Saimaa Gesture?
Thought
Let’s think step by step.
Adam Clayton Powell (film) is a documentary about
an African-American politician, not Finnish rock groups.
So the documentary
about Finnish rock groups must instead be The Saimaa Gesture.
Answer
The Saimaa Gesture
Question
What profession does Nicholas Ray and Elia Kazan have in common?
Thought
Let’s think step by step.
Professions of Nicholas Ray are director,
screenwriter, and actor.
Professions of Elia Kazan are director, producer,
screenwriter, and actor.
So profession Nicholas Ray and Elia Kazan have in
common is director, screenwriter, and actor.
Answer
director, screenwriter, actor
Question
Which magazine was started first Arthur’s Magazine or First for Women?
Thought
Let’s think step by step.
Arthur’s Magazine was started in 1844.
First
for Women was started in 1989.
1844 (Arthur’s Magazine) < 1989 (First for
Women), so Arthur’s Magazine was started first.
Answer
Arthur’s Magazine
Question
Were Pavel Urysohn and Leonid Levin known for the same type of work?
Thought
Let’s think step by step.
Pavel Urysohn is a mathematician.
Leonid Levin
is a mathematician and computer scientist.
So Pavel Urysohn and Leonid
Levin have the same type of work.
Answer
Yes
ReAct
Question
What is the elevation range for the area that the eastern sector of the
Colorado orogeny extends into?
Thought 1
I need to search Colorado orogeny, find the area that the eastern sector
of the Colorado orogeny extends into, then find the elevation range of the
area.
Action 1
Search[Colorado orogeny]
Observation 1
The Colorado orogeny was an episode of mountain building (an orogeny) in
Colorado and surrounding areas.
Thought 2
It does not mention the eastern sector.
So I need to look up eastern
sector.
Action 2
Lookup[eastern sector]
Observation 2
(Result 1 / 1) The eastern sector extends into the High Plains and is called
the Central Plains orogeny.
Thought 3
The eastern sector of Colorado orogeny extends into the High Plains.
So I
need to search High Plains and find its elevation range.
Action 3
Search[High Plains]
Observation 3
High Plains refers to one of two distinct land regions
Thought 4
I need to instead search High Plains (United States).
Action 4
Search[High Plains (United States)]
Continued on next page

###### 17


---
### 【第 18 页】


###### Published as a conference paper at ICLR 2023

Hotpot QA Prompts – Continued from previous page
Observation 4
The High Plains are a subregion of the Great Plains.
From east to west, the
High Plains rise in elevation from around 1,800 to 7,000 ft (550 to 2,130
m).[3]
Thought 5
High Plains rise in elevation from around 1,800 to 7,000 ft, so the answer
is 1,800 to 7,000 ft.
Action 5
Finish[1,800 to 7,000 ft]
Question
Musician and satirist Allie Goertz wrote a song about the "The Simpsons"
character Milhouse, who Matt Groening named after who?
Thought 1
The question simplifies to "The Simpsons" character Milhouse is named after
who.
I only need to search Milhouse and find who it is named after.
Action 1
Search[Milhouse]
Observation 1
Milhouse Mussolini Van Houten is a recurring character in the Fox animated
television series The Simpsons voiced by Pamela Hayden and created by Matt
Groening.
Thought 2
The paragraph does not tell who Milhouse is named after, maybe I can look up
"named after".
Action 2
Lookup[named after]
Observation 2
(Result 1 / 1) Milhouse was named after U.S. president Richard Nixon, whose
middle name was Milhous.
Thought 3
Milhouse was named after U.S. president Richard Nixon, so the answer is
Richard Nixon.
Action 3
Finish[Richard Nixon]
Question
Which documentary is about Finnish rock groups, Adam Clayton Powell or The
Saimaa Gesture?
Thought 1
I need to search Adam Clayton Powell and The Saimaa Gesture, and find which
documentary is about Finnish rock groups.
Action 1
Search[Adam Clayton Powell]
Observation 1
Could not find [Adam Clayton Powell].
Similar:
[’Adam Clayton Powell
III’, ’Seventh Avenue (Manhattan)’, ’Adam Clayton Powell Jr.
State Office
Building’, ’Isabel Washington Powell’, ’Adam Powell’, ’Adam Clayton Powell
(film)’, ’Giancarlo Esposito’].
Thought 2
To find the documentary, I can search Adam Clayton Powell (film).
Action 2
Search[Adam Clayton Powell (film)]
Observation 2
Adam Clayton Powell is a 1989 American documentary film directed by
Richard Kilberg.
The film is about the rise and fall of influential
African-American politician Adam Clayton Powell Jr.[3][4] It was later aired
as part of the PBS series The American Experience.
Thought 3
Adam Clayton Powell (film) is a documentary about an African-American
politician, not Finnish rock groups.
So the documentary about Finnish rock
groups must instead be The Saimaa Gesture.
Action 3
Finish[The Saimaa Gesture]
Question
What profession does Nicholas Ray and Elia Kazan have in common?
Thought 1
I need to search Nicholas Ray and Elia Kazan, find their professions, then
find the profession they have in common.
Action 1
Search[Nicholas Ray]
Observation 1
Nicholas Ray (born Raymond Nicholas Kienzle Jr., August 7, 1911 - June 16,
1979) was an American film director, screenwriter, and actor best known for
the 1955 film Rebel Without a Cause.
Thought 2
Professions of Nicholas Ray are director, screenwriter, and actor.
I need
to search Elia Kazan next and find his professions.
Action 2
Search[Elia Kazan]
Observation 2
Elia Kazan was an American film and theatre director, producer, screenwriter
and actor.
Thought 3
Professions of Elia Kazan are director, producer, screenwriter, and actor.
So profession Nicholas Ray and Elia Kazan have in common is director,
screenwriter, and actor.
Action 3
Finish[director, screenwriter, actor]
Question
Which magazine was started first Arthur’s Magazine or First for Women?
Thought 1
I need to search Arthur’s Magazine and First for Women, and find which was
started first.
Action 1
Search[Arthur’s Magazine]
Observation 1
Arthur’s Magazine (1844-1846) was an American literary periodical published
in Philadelphia in the 19th century.
Thought 2
Arthur’s Magazine was started in 1844.
I need to search First for Women
next.
Action 2
Search[First for Women]
Observation 2
First for Women is a woman’s magazine published by Bauer Media Group in the
USA.[1] The magazine was started in 1989.
Thought 3
First for Women was started in 1989.
1844 (Arthur’s Magazine) < 1989 (First
for Women), so Arthur’s Magazine was started first.
Action 3
Finish[Arthur’s Magazine]
Question
Were Pavel Urysohn and Leonid Levin known for the same type of work?
Thought 1
I need to search Pavel Urysohn and Leonid Levin, find their types of work,
then find if they are the same.
Action 1
Search[Pavel Urysohn]
Continued on next page

###### 18


---
### 【第 19 页】


###### Published as a conference paper at ICLR 2023

Hotpot QA Prompts – Continued from previous page
Observation 1
Pavel Samuilovich Urysohn (February 3, 1898 - August 17, 1924) was a Soviet
mathematician who is best known for his contributions in dimension theory.
Thought 2
Pavel Urysohn is a mathematician.
I need to search Leonid Levin next and
find its type of work.
Action 2
Search[Leonid Levin]
Observation 2
Leonid Anatolievich Levin is a Soviet-American mathematician and computer
scientist.
Thought 3
Leonid Levin is a mathematician and computer scientist.
So Pavel Urysohn
and Leonid Levin have the same type of work.
Action 3
Finish[yes]

###### 19


---
### 【第 20 页】


###### Published as a conference paper at ICLR 2023


###### C.2


###### FEVER

FEVER Prompts
Original
Determine if there is Observation that SUPPORTS or REFUTES a Claim, or if
there is NOT ENOUGH INFORMATION.
Claim
Nikolaj Coster-Waldau worked with the Fox Broadcasting Company.
Answer
SUPPORTS
Claim
Stranger Things is set in Bloomington, Indiana.
Answer
REFUTES
Claim
Beautiful reached number two on the Billboard Hot 100 in 2003.
Answer
NOT ENOUGH INFO
Act
Determine if there is Observation that SUPPORTS or REFUTES a Claim, or if
there is NOT ENOUGH INFORMATION.
Claim
Nikolaj Coster-Waldau worked with the Fox Broadcasting Company.
Action2
Search[Nikolaj Coster-Waldau]
Observation 1
Nikolaj William Coster-Waldau (born 27 July 1970) is a Danish actor and
producer.
He graduated from the Danish National School of Performing Arts
in Copenhagen in 1993,[1] and had his breakthrough role in Denmark with
the film Nightwatch (1994).
He played Jaime Lannister in the HBO fantasy
drama series Game of Thrones, for which he received two Primetime Emmy
Award nominations for Outstanding Supporting Actor in a Drama Series..
Coster-Waldau has appeared in numerous films in his native Denmark and
Scandinavia, including Headhunters (2011) and A Thousand Times Good Night
(2013).
In the U.S, his debut film role was in the war film Black Hawk Down
(2001), playing Medal of Honor recipient Gary Gordon.[2] He then played a
detective in the short-lived Fox television series New Amsterdam (2008), and
appeared in the 2009 Fox television film Virtuality, originally intended as
a pilot.
Action 2
Finish[SUPPORTS]
Claim
Stranger Things is set in Bloomington, Indiana.
Action 1
Search[Stranger Things]
Observation 1
Stranger Things is an American science fiction horror drama television
series created by the Duffer Brothers.
Set in the 1980s, primarily in
the fictional town of Hawkins, Indiana, the series centers on a number of
mysteries and supernatural events occurring around the town and their impact
on an ensemble of child and adult characters.
Action 2
Finish[REFUTES]
Claim
Beautiful reached number two on the Billboard Hot 100 in 2003.
Action 1
Search[Beautiful]
Observation 1
Could not find [Beautiful].
Similar:
[’Beautiful’, ’Beautiful, Beautiful’,
’A Beautiful Mind (film)’, ’Beautiful (Christina Aguilera song)’, ’Life Is
Beautiful’].
Action 2
Search[Beautiful (Christina Aguilera song)
Observation 2
"Beautiful" is a song recorded by American singer Christina Aguilera for her
fourth studio album, Stripped (2002).
Action 3
Lookup[Billboard Hot 100]
Observation 3
(Result 1 / 3) The song peaked at number two on the Billboard Hot 100 in the
United States, where it was certified Gold for 500,000 units shipped.
Action 4
Finish[NOT ENOUGH INFO]
CoT
Determine if there is Observation that SUPPORTS or REFUTES a Claim, or if
there is NOT ENOUGH INFORMATION.
Claim
Nikolaj Coster-Waldau worked with the Fox Broadcasting Company.
Thought
Nikolaj William Coster-Waldau appeared in the 2009 Fox television film
Virtuality, so he has worked with the Fox Broadcasting Company.
Answer
SUPPORTS
Claim
Stranger Things is set in Bloomington, Indiana.
Thought
Stranger Things is in the fictional town of Hawkins, Indiana, not in
Bloomington, Indiana.
Answer
REFUTES
Continued on next page

###### 20


---
### 【第 21 页】


###### Published as a conference paper at ICLR 2023

Fever Prompts – Continued from previous page
Claim
Beautiful reached number two on the Billboard Hot 100 in 2003.
Thought
The song peaked at number two on the Billboard Hot 100 in the United States,
but not sure if it was in 2003.
Answer
NOT ENOUGH INFO
ReAct
Determine if there is Observation that SUPPORTS or REFUTES a Claim, or if
there is NOT ENOUGH INFORMATION.
Claim
Nikolaj Coster-Waldau worked with the Fox Broadcasting Company.
Thought 1
I need to search Nikolaj Coster-Waldau and find if he has worked with the
Fox Broadcasting Company.
Action 1
Search[Nikolaj Coster-Waldau]
Observation 1
Nikolaj William Coster-Waldau (born 27 July 1970) is a Danish actor and
producer.
He graduated from the Danish National School of Performing Arts
in Copenhagen in 1993,[1] and had his breakthrough role in Denmark with
the film Nightwatch (1994).
He played Jaime Lannister in the HBO fantasy
drama series Game of Thrones, for which he received two Primetime Emmy
Award nominations for Outstanding Supporting Actor in a Drama Series..
Coster-Waldau has appeared in numerous films in his native Denmark and
Scandinavia, including Headhunters (2011) and A Thousand Times Good Night
(2013).
In the U.S, his debut film role was in the war film Black Hawk Down
(2001), playing Medal of Honor recipient Gary Gordon.[2] He then played a
detective in the short-lived Fox television series New Amsterdam (2008), and
appeared in the 2009 Fox television film Virtuality, originally intended as
a pilot.
Thought 2
Because he "appeared in the 2009 Fox television film Virtuality", he should
have worked with the Fox Broadcasting Company.
Action 2
Finish[SUPPORTS]
Claim
Stranger Things is set in Bloomington, Indiana.
Thought 1
I should search for Stranger Things, and see if it is set in Bloomington,
Indiana.
Action 1
Search[Stranger Things]
Observation 1
Stranger Things is an American science fiction horror drama television
series created by the Duffer Brothers.
Set in the 1980s, primarily in
the fictional town of Hawkins, Indiana, the series centers on a number of
mysteries and supernatural events occurring around the town and their impact
on an ensemble of child and adult characters.
Thought 2
The observation says that it is set in a "fictional town of Hawkins,
Indiana", so it is not set in Bloomington.
Action 2
Finish[REFUTES]
Claim
Beautiful reached number two on the Billboard Hot 100 in 2003.
Thought 1
I need to search the song Beautiful and find if it reached number two on the
Billboard Hot 100 in 2003.
Action 1
Search[Beautiful]
Observation 1
Could not find [Beautiful].
Similar:
[’Beautiful’, ’Beautiful, Beautiful’,
’A Beautiful Mind (film)’, ’Beautiful (Christina Aguilera song)’, ’Life Is
Beautiful’].
Thought 2
From suggestions, I should search "Beautiful (Christina Aguilera song)" to
find the song.
Action 2
Search[Beautiful (Christina Aguilera song)]
Observation 2
"Beautiful" is a song recorded by American singer Christina Aguilera for her
fourth studio album, Stripped (2002).
Thought 3
It does not mention Billboard, so I need to look up "Billboard Hot 100" to
find if it reached number two on it in 2003.
Action 3
Lookup[Billboard Hot 100]
Observation 3
(Result 1 / 3) The song peaked at number two on the Billboard Hot 100 in the
United States, where it was certified Gold for 500,000 units shipped.
Thought 4
It only says the song peaked at number two on the Billboard Hot 100, but not
if it was in 2003.
I am not sure if this claim is true or not.
Action 4
Finish[NOT ENOUGH INFO]

###### 21


---
### 【第 22 页】


###### Published as a conference paper at ICLR 2023


###### C.3


###### WEBSHOP


###### Table 6: Prompts used for the Webshop experiments in Section 4. We use the prompt on the left for


###### Act, and use the prompt on the right (add reasoning) for ReAct.

Instruction: i would like a 3 ounce bottle of bright citrus deodorant for sensitive skin, and price lower than 50.00 dollars
Act
ReAct
Action: search
�
3 ounce bright citrus deodorant sensitive skin
�
Observation:
�
Back to Search
�
Page 1 (Total results: 50)
�
Next
�
�
B078GWRC1J
�
Bright Citrus Deodorant by Earth Mama | Natural and Safe for
Sensitive Skin, Pregnancy and Breastfeeding, Contains Organic
Calendula 3-Ounce
$10.99
�
B078GTKVXY
�
Ginger Fresh Deodorant by Earth Mama | Natural and Safe for
Sensitive Skin, Pregnancy and Breastfeeding, Contains Organic
Calendula 3-Ounce
$10.99
�
B08KBVJ4XN
�
Barrel and Oak - Aluminum-Free Deodorant, Deodorant for Men
, Essential Oil-Based Scent, 24-Hour Odor Protection, Cedar
& Patchouli Blend, Gentle on Sensitive Skin (Mountain Sage,
2.7 oz, 2-Pack)
$15.95
Action: click
�
B078GWRC1J
�
Observation:
�
Back to Search
�
�
Prev
�
scent [assorted scents][bright citrus][calming lavender][ginger
[fresh] simply non-scents]
size [travel set (4-pack)][3 ounce (pack of 1)][3-ounce (2
-pack)]
Bright Citrus Deodorant by Earth Mama | Natural and Safe for
Sensitive Skin, Pregnancy and Breastfeeding, Contains Organic
Calendula 3-Ounce
Price: $10.99
Rating: N.A.
[Description]
[Features]
[Reviews]
[Buy Now]
Action: click[bright citrus]
Observation: You have clicked bright citrus.
Action: click[3 ounce (pack of 1)]
Observation: You have clicked 3 ounce (pack of 1).
Action: click[Buy Now]
Action: search
�
3 ounce bright citrus deodorant sensitive skin
Observation:
�
Back to Search
�
Page 1 (Total results: 50)
�
Next
�
�
B078GWRC1J
�
Bright Citrus Deodorant by Earth Mama | Natural and Safe for
Sensitive Skin, Pregnancy and Breastfeeding, Contains Organic
Calendula 3-Ounce
$10.99
�
B078GTKVXY
�
Ginger Fresh Deodorant by Earth Mama | Natural and Safe for
Sensitive Skin, Pregnancy and Breastfeeding, Contains Organic
Calendula 3-Ounce
$10.99
�
B08KBVJ4XN
�
Barrel and Oak - Aluminum-Free Deodorant, Deodorant for Men
, Essential Oil-Based Scent, 24-Hour Odor Protection, Cedar
& Patchouli Blend, Gentle on Sensitive Skin (Mountain Sage,
2.7 oz, 2-Pack)
$15.95
Action: think[B078GWRC1J and B078GTKVXY are bright citrus
deodorant less then 50 dollars. I can check B078GWRC1J first.
Observation: OK.
Action: click
�
B078GWRC1J
�
Observation:
�
Back to Search
�
�
Prev
�
scent [assorted scents][bright citrus][calming lavender][ginger
[fresh] simply non-scents]
size [travel set (4-pack)][3 ounce (pack of 1)][3-ounce (2
-pack)]
Bright Citrus Deodorant by Earth Mama | Natural and Safe for
Sensitive Skin, Pregnancy and Breastfeeding, Contains Organic
Calendula 3-Ounce
Price: $10.99
Rating: N.A.
[Description]
[Features]
[Reviews]
[Buy Now]
Action: think[For 3 ounce bottle of bright citrus deodorant
for sensitive skin, the item has options ’bright citrus’
and ’3 ounce (pack of 1)’ and seems good to buy.]
Observation: OK.
Action: click[bright citrus]
Observation: You have clicked bright citrus.
Action: click[3 ounce (pack of 1)]
Observation: You have clicked 3 ounce (pack of 1).
Action: click[Buy Now]

###### 22


---
### 【第 23 页】


###### Published as a conference paper at ICLR 2023


###### C.4


###### ALFWORLD


###### Table 7: An Act prompt on the ALFWorld clean task. No thoughts are provided.

You are in the middle of a room.
Looking quickly around you, you see a cabinet
13, a cabinet 12, a cabinet 11, a cabinet 10, a cabinet 9, a cabinet 8, a cabinet
7, a cabinet 6, a cabinet 5, a cabinet 4, a cabinet 3, a cabinet 2, a cabinet
1, a coffeemachine 1, a countertop 1, a diningtable 1, a drawer 1, a fridge 1, a
garbagecan 1, a microwave 1, a shelf 3, a shelf 2, a shelf 1, a sinkbasin 1, a
stoveburner 4, a stoveburner 3, a stoveburner 2, a stoveburner 1, and a toaster 1.
Your task is to:
put a clean lettuce in diningtable.
> go to fridge 1
The fridge 1 is closed.
> open fridge 1
You open the fridge 1.
The fridge 1 is open.
In it, you see a cup 3, a egg 2, a
potato 3, and a potato 2.
> go to diningtable 1
On the diningtable 1, you see a apple 1, a bread 1, a butterknife 2, a cup 2, a
fork 2, a knife 2, a knife 1, a ladle 1, a lettuce 1, a mug 2, a mug 1, a pan 2, a
peppershaker 1, a spatula 3, a tomato 2, and a tomato 1.
> take lettuce 1 from diningtable 1
You pick up the lettuce 1 from the diningtable 1.
> go to sinkbasin 1
On the sinkbasin 1, you see a apple 2, a ladle 2, a spoon 1, and a tomato 3.
> clean lettuce 1 with sinkbasin 1
You clean the lettuce 1 using the sinkbasin 1.
> think:
Now I clean a lettuce (1).
Next, I need to put it in/on diningtable 1.
OK.
> go to diningtable 1
On the diningtable 1, you see a apple 1, a bread 1, a butterknife 2, a cup 2, a fork
2, a knife 2, a knife 1, a ladle 1, a mug 2, a mug 1, a pan 2, a peppershaker 1, a
spatula 3, a tomato 2, and a tomato 1.
> put lettuce 1 in/on diningtable 1
You put the lettuce 1 in/on the diningtable 1.

###### 23


---
### 【第 24 页】


###### Published as a conference paper at ICLR 2023


###### Table 8: An ReAct prompt on the ALFWorld clean task.

You are in the middle of a room.
Looking quickly around you, you see a cabinet
13, a cabinet 12, a cabinet 11, a cabinet 10, a cabinet 9, a cabinet 8, a cabinet
7, a cabinet 6, a cabinet 5, a cabinet 4, a cabinet 3, a cabinet 2, a cabinet
1, a coffeemachine 1, a countertop 1, a diningtable 1, a drawer 1, a fridge 1, a
garbagecan 1, a microwave 1, a shelf 3, a shelf 2, a shelf 1, a sinkbasin 1, a
stoveburner 4, a stoveburner 3, a stoveburner 2, a stoveburner 1, and a toaster 1.
Your task is to:
put a clean lettuce in diningtable.
> think:
To solve the task, I need to find and take a lettuce, then clean it with
sinkbasin, then put it in diningtable.
OK.
> think:
First I need to find a lettuce.
A lettuce is more likely to appear in
fridge (1), diningtable (1), sinkbasin (1), stoveburner (1-3), cabinet (1-13).
I
can check one by one, starting with fridge 1.
OK.
> go to fridge 1
The fridge 1 is closed.
> open fridge 1
You open the fridge 1.
The fridge 1 is open.
In it, you see a cup 3, a egg 2, a
potato 3, and a potato 2.
> go to diningtable 1
On the diningtable 1, you see a apple 1, a bread 1, a butterknife 2, a cup 2, a
fork 2, a knife 2, a knife 1, a ladle 1, a lettuce 1, a mug 2, a mug 1, a pan 2, a
peppershaker 1, a spatula 3, a tomato 2, and a tomato 1.
> think:
Now I find a lettuce (1).
Next, I need to take it.
OK.
> take lettuce 1 from diningtable 1
You pick up the lettuce 1 from the diningtable 1.
> think:
Now I take a lettuce (1).
Next, I need to go to sinkbasin (1) and clean
it.
OK.
> go to sinkbasin 1
On the sinkbasin 1, you see a apple 2, a ladle 2, a spoon 1, and a tomato 3.
> clean lettuce 1 with sinkbasin 1
You clean the lettuce 1 using the sinkbasin 1.
> think:
Now I clean a lettuce (1).
Next, I need to put it in/on diningtable 1.
OK.
> go to diningtable 1
On the diningtable 1, you see a apple 1, a bread 1, a butterknife 2, a cup 2, a fork
2, a knife 2, a knife 1, a ladle 1, a mug 2, a mug 1, a pan 2, a peppershaker 1, a
spatula 3, a tomato 2, and a tomato 1.
> put lettuce 1 in/on diningtable 1
You put the lettuce 1 in/on the diningtable 1.

###### 24


---
### 【第 25 页】


###### Published as a conference paper at ICLR 2023


###### Table 9: An ReAct-IM prompt on the ALFWorld clean task.

You are in the middle of a room.
Looking quickly around you, you see a cabinet
13, a cabinet 12, a cabinet 11, a cabinet 10, a cabinet 9, a cabinet 8, a cabinet
7, a cabinet 6, a cabinet 5, a cabinet 4, a cabinet 3, a cabinet 2, a cabinet
1, a coffeemachine 1, a countertop 1, a diningtable 1, a drawer 1, a fridge 1, a
garbagecan 1, a microwave 1, a shelf 3, a shelf 2, a shelf 1, a sinkbasin 1, a
stoveburner 4, a stoveburner 3, a stoveburner 2, a stoveburner 1, and a toaster 1.
Your task is to:
put a clean lettuce in diningtable.
> think:
To solve the task, I need to find and take a lettuce, then clean it with
sinkbasin, then put it in diningtable.
OK.
> think:
First I need to find a lettuce.
OK.
> go to fridge 1
The fridge 1 is closed.
> think:
First I need to find a lettuce.
OK.
> open fridge 1
You open the fridge 1.
The fridge 1 is open.
In it, you see a cup 3, a egg 2, a
potato 3, and a potato 2.
> think:
First I need to find a lettuce.
OK.
> go to diningtable 1
On the diningtable 1, you see a apple 1, a bread 1, a butterknife 2, a cup 2, a
fork 2, a knife 2, a knife 1, a ladle 1, a lettuce 1, a mug 2, a mug 1, a pan 2, a
peppershaker 1, a spatula 3, a tomato 2, and a tomato 1.
> think:
First I need to find a lettuce.
OK.
> take lettuce 1 from diningtable 1
You pick up the lettuce 1 from the diningtable 1.
> think:
I need to clean this lettuce (1) using sinkbasin 1.
OK.
> go to sinkbasin 1
On the sinkbasin 1, you see a apple 2, a ladle 2, a spoon 1, and a tomato 3.
> think:
I need to clean this lettuce (1) using sinkbasin 1.
OK.
> clean lettuce 1 with sinkbasin 1
You clean the lettuce 1 using the sinkbasin 1.
> think:
I need to put this cleaned lettuce (1) in/on diningtable 1.
OK.
> go to diningtable 1
On the diningtable 1, you see a apple 1, a bread 1, a butterknife 2, a cup 2, a fork
2, a knife 2, a knife 1, a ladle 1, a mug 2, a mug 1, a pan 2, a peppershaker 1, a
spatula 3, a tomato 2, and a tomato 1.
> think:
I need to put this cleaned lettuce (1) in/on diningtable 1.
OK.
> put lettuce 1 in/on diningtable 1
You put the lettuce 1 in/on the diningtable 1.

###### D


###### TRAJECTORIES


###### D.1


###### FEVER TRAJECTORIES


###### We provide some trajectories produced by ReAct, CoTand Acton several randomly selected exam-


###### ples from the FEVER dev set below. Search results are omitted to space.


###### 25


---
### 【第 26 页】


###### Published as a conference paper at ICLR 2023

Example 2491 (gt: REFUTES)
ReAct
Claim:
Bermuda Triangle is a loosely-defined region in the Pacific Ocean.
Thought 1:
I need to search Bermuda Triangle and find if it is in the Pacific Ocean.
Action 1:
Search[Bermuda Triangle]
Observation 1:
Reportedly haunted locations...
Thought 2:
The observation says that it is in the western part of the North Atlantic
Ocean, so it is not in the Pacific Ocean.
Action 2:
Finish[REFUTES]
Observation 2:
Episode finished
Act
Claim:
Bermuda Triangle is a loosely-defined region in the Pacific Ocean.
Action 1
:
Search[Bermuda Triangle]
Observation 1
:
Reportedly haunted locations:...
Action 2:
Finish[REFUTES]
Observation 2:
Episode finished
CoT
Claim:
Bermuda Triangle is a loosely-defined region in the Pacific Ocean.
Thought:
Let’s think step by step.
The Bermuda Triangle is a loosely-defined region
in the Atlantic Ocean.
The Pacific Ocean is not the Atlantic Ocean.
Answer:
REFUTES
Example 5908 (gt: SUPPORTS)
ReAct
Claim:
Princess Mononoke is a film.
Thought 1:
I need to search Princess Mononoke and find if it is a film.
Action 1:
Search[Princess Mononoke]
Observation 1:
Princess Mononoke ...
Thought 2:
From the observation, it says that Princess Mononoke is a film.
Action 2:
Finish[SUPPORTS]
Observation 2:
Episode finished
Act
Claim:
Princess Mononoke is a film.
Action 1:
Search[Princess Mononoke]
Observation 1:
Princess Mononoke ...
Action 2:
Finish[SUPPORTS]
Observation 2:
Episode finished
CoT
Claim:
Princess Mononoke is a film.
Thought:
Let’s think step by step.
Princess Mononoke is a movie, and movies are
films.
Answer:
SUPPORTS
Example 1951 (gt: REFUTES)
ReAct
Claim:
Soyuz was part of the American space program.
Thought 1:
I need to search Soyuz and find if it was part of the American space
program.
Action 1:
Search[Soyuz]
Observation 1:
Soyuz is a transliteration...
Thought 2:
It does not mention the American space program, so I need to search
"American space program" to find if it was part of it.
Action 2:
Search[American space program]
Observation 2:
The space policy...
Thought 3:
It does not mention Soyuz, so I am not sure if this claim is true or not.
Action 3:
Finish[NOT ENOUGH INFO]
Observation 3:
Episode finished
Act
Claim:
Soyuz was part of the American space program.
Action 1:
Search[Soyuz]
Observation 1:
Soyuz is a transliteration...
Action 2:
Finish[NOT ENOUGH INFO]
Observation 2:
Episode finished
CoT
Claim:
Soyuz was part of the American space program.
Thought:
Let’s think step by step.
Soyuz is a Russian spacecraft.
The American
space program is NASA. NASA and Russia have worked together on the
International Space Station.
Answer:
SUPPORTS

###### 26


---
### 【第 27 页】


###### Published as a conference paper at ICLR 2023

Example 3208 (gt: REFUTES)
ReAct
Claim:
Reign Over Me is an American film made in 2010.
Thought 1:
I need to search for Reign Over Me and find if it is an American film made
in 2010.
Action 1:
Search[Reign Over Me]
Observation 1:
Reign Over Me ...
Thought 2:
The observation says that it is an American film made in 2007, so it is not
made in 2010.
Action 2:
Finish[REFUTES]
Observation 2:
Episode finished
Act
Claim:
Reign Over Me is an American film made in 2010.
Action 1:
Search[Reign Over Me]
Action 2:
Finish[SUPPORTS]
Observation 2:
Episode finished
CoT
Claim:
Reign Over Me is an American film made in 2010.
Thought:
Let’s think step by step.
First, is Reign Over Me an American film?
Yes,
it is.
Second, was it made in 2010?
Yes, it was.
Answer:
SUPPORTS

###### D.2


###### ALFWORLD TRAJECTORIES


###### We provide an example trajectory of ReAct, Act, and ReAct-IM on the same ALFWorld game,


###### pick_clean_then_place_in_recep-Knife-None-CounterTop-10/


###### trial_T20190909_110445_675754.


###### D.2.1


###### REACT TRAJECTORY


###### ReAct is able to correctly find the knife, clean it, and then place it on a countertop.


###### 27


---
### 【第 28 页】


###### Published as a conference paper at ICLR 2023

ReAct ALFWorld trajectory
You are in the middle of a room.
Looking quickly around you, you see a cabinet 6, a
cabinet 5, a cabinet 4, a cabinet 3, a cabinet 2, a cabinet 1, a coffeemachine 1, a
countertop 3, a countertop 2, a countertop 1, a drawer 3, a drawer 2, a drawer 1, a
fridge 1, a garbagecan 1, a microwave 1, a shelf 3, a shelf 2, a shelf 1, a sinkbasin
1, a stoveburner 4, a stoveburner 3, a stoveburner 2, a stoveburner 1, and a toaster
1.
Your task is to:
put a clean knife in countertop.
> think:
To solve the task, I need to find and take a knife, then clean it with
sinkbasin, then put it in countertop.
OK.
> think:
First I need to find a knife.
A knife is more likely to appear in cabinet
(1-6), drawer (1-3), countertop (1-3), fridge (1), garbagecan (1), shelf (1-3),
sinkbasin (1), stoveburner (1-4), toaster (1).
I can check one by one, starting with
cabinet 1.
OK.
> go to cabinet 1
On the cabinet 1, you see a bowl 1.
> go to cabinet 2
The cabinet 2 is closed.
> go to cabinet 3
On the cabinet 3, you see a glassbottle 1.
> go to cabinet 4
On the cabinet 4, you see a mug 1.
> go to cabinet 5
The cabinet 5 is closed.
> go to cabinet 6
The cabinet 6 is closed.
> go to drawer 1
The drawer 1 is closed.
> go to drawer 2
The drawer 2 is closed.
> go to drawer 3
The drawer 3 is closed.
> go to countertop 1
On the countertop 1, you see a lettuce 2, a mug 2, a peppershaker 1, and a spoon 2.
> go to countertop 2
On the countertop 2, you see a cup 1, a dishsponge 1, a glassbottle 3, a knife 1, a
plate 2, a potato 3, and a statue 1.
> think:
Now I find a knife (1).
Next, I need to take it.
OK.
> take knife 1 from countertop 2
You pick up the knife 1 from the countertop 2.
> think:
Now I take a knife (1).
Next, I need to go to sinkbasin (1) and clean it.
OK.
> go to sinkbasin 1
On the sinkbasin 1, you see a fork 3, a lettuce 3, and a spatula 2.
> clean knife 1 with sinkbasin 1
You clean the knife 1 using the sinkbasin 1.
> think:
Now I clean a knife (1).
Next, I need to put it in/on countertop 1.
OK.
> go to countertop 1
On the countertop 1, you see a lettuce 2, a mug 2, a peppershaker 1, and a spoon 2.
> put knife 1 in/on countertop 1
You put the knife 1 in/on the countertop 1.

###### D.2.2


###### ACT TRAJECTORY


###### Act is able to correctly find the knife, but tries to clean it using a sinkbasin before actually going


###### to the sinkbasin. From there on, the model is unable to recover, and is stuck repeating the same


###### sequence of commands. With ReAct, an existing thought would have concretely identified that the


###### knife had been taken, and that the next subgoal was to go to a sinkbasin to clean it.


###### 28


---
### 【第 29 页】


###### Published as a conference paper at ICLR 2023

Act ALFWorld trajectory
You are in the middle of a room.
Looking quickly around you, you see a cabinet 6, a
cabinet 5, a cabinet 4, a cabinet 3, a cabinet 2, a cabinet 1, a coffeemachine 1, a
countertop 3, a countertop 2, a countertop 1, a drawer 3, a drawer 2, a drawer 1, a
fridge 1, a garbagecan 1, a microwave 1, a shelf 3, a shelf 2, a shelf 1, a sinkbasin
1, a stoveburner 4, a stoveburner 3, a stoveburner 2, a stoveburner 1, and a toaster
1.
Your task is to:
put a clean knife in countertop.
> go to countertop 1
On the countertop 1, you see a lettuce 2, a mug 2, a peppershaker 1, and a spoon 2.
> go to countertop 2
On the countertop 2, you see a cup 1, a dishsponge 1, a glassbottle 3, a knife 1, a
plate 2, a potato 3, and a statue 1.
> take knife 1 from countertop 2
You pick up the knife 1 from the countertop 2.
> go to countertop 1
On the countertop 1, you see a lettuce 2, a mug 2, a peppershaker 1, and a spoon 2.
> clean knife 1 with sinkbasin 1
Nothing happens.
> go to countertop 3
On the countertop 3, you see a bread 3, a butterknife 2, a cellphone 1, a creditcard
1, a fork 2, a houseplant 1, a knife 2, a spatula 1, a statue 3, a tomato 3, a tomato
2, a tomato 1, and a vase 2.
> take knife 2 from countertop 3
Nothing happens.
> go to countertop 2
On the countertop 2, you see a cup 1, a dishsponge 1, a glassbottle 3, a plate 2, a
potato 3, and a statue 1.
> take knife 1 from countertop 2
Nothing happens.
> go to countertop 1
On the countertop 1, you see a lettuce 2, a mug 2, a peppershaker 1, and a spoon 2.
> clean knife 1 with sinkbasin 1
Nothing happens.
> go to countertop 3
On the countertop 3, you see a bread 3, a butterknife 2, a cellphone 1, a creditcard
1, a fork 2, a houseplant 1, a knife 2, a spatula 1, a statue 3, a tomato 3, a tomato
2, a tomato 1, and a vase 2.
> take knife 2 from countertop 3
Nothing happens.
> go to countertop 2
On the countertop 2, you see a cup 1, a dishsponge 1, a glassbottle 3, a plate 2, a
potato 3, and a statue 1.
> take knife 1 from countertop 2
Nothing happens.
> go to countertop 1
On the countertop 1, you see a lettuce 2, a mug 2, a peppershaker 1, and a spoon 2.
> clean knife 1 with sinkbasin 1
Nothing happens.
> go to countertop 3
On the countertop 3, you see a bread 3, a butterknife 2, a cellphone 1, a creditcard
1, a fork 2, a houseplant 1, a knife 2, a spatula 1, a statue 3, a tomato 3, a tomato
2, a tomato 1, and a vase 2.
> take knife 2 from countertop 3
Nothing happens.
> go to countertop 2
On the countertop 2, you see a cup 1, a dishsponge 1, a glassbottle 3, a plate 2, a
potato 3, and a statue 1.
> take knife 1 from countertop 2
Nothing happens.
> go to countertop 1
On the countertop 1, you see a lettuce 2, a mug 2, a peppershaker 1, and a spoon 2.
> clean knife 1 with sinkbasin 1
Nothing happens.

###### D.2.3


###### REACT-IM TRAJECTORY


###### ReAct-IM is able to correctly find the knife, but is unable to clean it as well. The LLM then


###### gets stuck trying to place this knife on a countertop. One possible issue is the incorrect thought


###### think:


###### I need to find a clean knife., which seems to trick the LLM in believing


###### that the knife is already cleaned. In ReAct, this sequence of subgoals would be concretely captured


###### by each thought.


###### 29


---
### 【第 30 页】


###### Published as a conference paper at ICLR 2023

ReAct-IM ALFWorld trajectory
You are in the middle of a room.
Looking quickly around you, you see a cabinet 6, a
cabinet 5, a cabinet 4, a cabinet 3, a cabinet 2, a cabinet 1, a coffeemachine 1, a
countertop 3, a countertop 2, a countertop 1, a drawer 3, a drawer 2, a drawer 1, a
fridge 1, a garbagecan 1, a microwave 1, a shelf 3, a shelf 2, a shelf 1, a sinkbasin
1, a stoveburner 4, a stoveburner 3, a stoveburner 2, a stoveburner 1, and a toaster
1.
Your task is to:
put a clean knife in countertop.
> think:
To solve the task, I need to find and take a clean knife, then put it in
countertop.
OK.
> think:
I need to find a clean knife.
OK.
> go to countertop 1
On the countertop 1, you see a lettuce 2, a mug 2, a peppershaker 1, and a spoon 2.
> think:
I need to find a clean knife.
OK.
> go to countertop 2
On the countertop 2, you see a cup 1, a dishsponge 1, a glassbottle 3, a knife 1, a
plate 2, a potato 3, and a statue 1.
> think:
I need to find a clean knife.
OK.
> take knife 1 from countertop 2
You pick up the knife 1 from the countertop 2.
> think:
I need to put this knife (1) in/on countertop 1.
OK.
> go to countertop 1
On the countertop 1, you see a lettuce 2, a mug 2, a peppershaker 1, and a spoon 2.
> think:
I need to put this knife (1) in/on countertop 1.
OK.
> put knife 1 in/on countertop 1
You put the knife 1 in/on the countertop 1.
> think:
I need to put this knife (1) in/on countertop 1.
OK.
> put knife 1 in/on countertop 1
Nothing happens.
> think:
I need to put this knife (1) in/on countertop 1.
OK.
> put knife 1 in/on countertop 1
Nothing happens.
> think:
I need to put this knife (1) in/on countertop 1.
OK.
> put knife 1 in/on countertop 1
Nothing happens.
> think:
I need to put this knife (1) in/on countertop 1.
OK.
> put knife 1 in/on countertop 1
Nothing happens.
> think:
I need to put this knife (1) in/on countertop 1.
OK.
> put knife 1 in/on countertop 1
Nothing happens.
> think:
I need to put this knife (1) in/on countertop 1.
OK.

###### 30


---
### 【第 31 页】


###### Published as a conference paper at ICLR 2023


###### D.3


###### WEBSHOP TRAJECTORIES


###### Table 10: Example trajectories for Webshop predicted by Act and ReAct. Compared to Act,


###### ReAct uses reasoning to find products that satisfy all target attributes.

Instruction: get me a sixteen pack of apple cinnamon freeze dried banana chips, and price lower than 50.00 dollars
Act
ReAct
Action: search
�
sixteen pack apple cinnamon freeze dried banana
chips
�
Observation:
�
Back to Search
�
Page 1 (Total results: 50)
�
Next
�
�
B0061IVFZE
�
Brothers-ALL-Natural Fruit Crisps, Strawberry Banana, 0.42 -
Ounce (Pack of 100)
$85.0
�
B096H2P6G2
�
Moon Fruit Freeze Dried Fruit Snacks. Fruit Snacks for Kids -
(Variety Pack)
$18.99
�
B092JLLYK6
�
Nature’s Turn Freeze-Dried Fruit Snacks - Banana Crisps - Perfect
For School Lunches or an On-The-Go Snack - No Sugar Added,
Non GMO, Gluten Free, Nothing Artificial (0.53oz) 6-Pack
$12.99
Action: click
�
B0061IVFZE
�
Observation:
�
Back to Search
�
�
Prev
�
flavor name [asian pear][banana][fuji apple & cinnamon][strawberry
banana] Brothers-ALL-Natural Fruit Crisps, Strawberry Banana,
0.42 Ounce (Pack of 100)
Price: $85.0
Rating: N.A.
[Description]
[Features]
[Reviews]
[Buy Now]
Action: click[Buy Now]
Action: search
�
sixteen pack apple cinnamon freeze dried banana
chips
�
Observation:
�
Back to Search
�
Page 1 (Total results: 50)
�
Next
�
�
B0061IVFZE
�
Brothers-ALL-Natural Fruit Crisps, Strawberry Banana, 0.42 -
Ounce (Pack of 100)
$85.0
�
B096H2P6G2
�
Moon Fruit Freeze Dried Fruit Snacks. Fruit Snacks for Kids -
(Variety Pack)
$18.99
�
B092JLLYK6
�
Nature’s Turn Freeze-Dried Fruit Snacks - Banana Crisps - Perfect
For School Lunches or an On-The-Go Snack - No Sugar Added,
Non GMO, Gluten Free, Nothing Artificial (0.53oz) 6-Pack
$12.99
Action: think[B0061IVFZE is strawberry banana, not apple cinnamon.
B096H2P6G2 is fruit snacks, not freeze dried banana chips.
B092JLLYK6 is banana crisps, not apple cinnamon. I can check
B092JLLYK6 first.
Observation: OK.
Action: click
�
B092JLLYK6
�
Observation:
�
Back to Search
�
�
Prev
�
flavor name [apple][apple cinnamon][banana][cantaloupe][peach][pear]
[strawberry][strawberry banana][sampler variety pack][mega variety
pack][orchard variety pack]
size [0.53 ounce (pack of 6)][0.53 ounce (pack of 8)][0.53 ounce (pack
of 16)]
Nature’s Turn Freeze-Dried Fruit Snacks - Banana Crisps - Perfect
For School Lunches or an On-The-Go Snack - No Sugar Added, Non
GMO, Gluten Free, Nothing Artificial (0.53oz) 6-Pack
Price: $12.99
Rating: N.A.
[Description]
[Features]
[Reviews]
[Buy Now]
Action: think[For sixteen pack of apple cinnamon freeze dried banana
chips, the item has options ’apple cinnamon’ and ’0.53 ounce (pack of
16)’ and seems good to buy.]
Observation: OK.
Action: click[apple cinnamon]
Observation: You have clicked apple cinnamon.
Action: click[0.53 ounce (pack of 16)]
Observation: You have clicked 0.53 ounce (pack of 16).
Action: click[Buy Now]
Score: 0.125
Score: 1.0

###### 31


---
### 【第 32 页】


###### Published as a conference paper at ICLR 2023


###### E


###### MORE ANALYSIS


###### E.1


###### SUCCESS AND FAILURE MODES ANALYSIS


###### We provide some examples corresponding to the success and error mode analysis given in Sec. 3.3.


###### Search results and non-representative steps are omitted to reduce space.

Success: True positive
ReAct
Question:
Author David Chanoff has collaborated with a U.S. Navy admiral who served as
the ambassador to the United Kingdom under which President?
Thought 1:
I need to search David Chanoff and find the U.S. Navy admiral he
collaborated with.
Action 1:
Search[David Chanoff]
Observation 1:
David Chanoff is a noted author...
Action 2:
Search[William J. Crowe]
Observation 2:
William J. Crowe is...
Thought 3:
William J. Crowe served as the ambassador to the United Kingdom under
President Bill Clinton.
So the answer is Bill Clinton.
Action 3:
Finish[Bill Clinton]
Observation 3:
Episode finished
CoT
Question:
What was the name of the team that represented an Arizona university in
the conference that covers a broad expanse of the western United States,
including Arizona, California, and New Mexico?
Thought:
Let’s think step by step.
The name of the team that represented an Arizona
university in the conference that covers a broad expanse of the western
United States, including Arizona, California, and New Mexico is Arizona
State Sun Devils.
Answer:
Arizona State Sun Devils
Success: False positive
ReAct
Question:
Did the board game San Marco or About Time come out first?
Thought 1:
I need to search San Marco and About Time, and find which came out first.
Action 1:
Search[San Marco]
Observation 1:
San Marco is one of the ...
The was built in venice.
Thought 2:
San Marco is a sestiere of Venice.
I need to search About Time next.
Action 2:
Search[About Time]
Observation 2:
Could not find [About Time].
Similar:
[...].
Thought 3:
About Time is a 2013 film.
So San Marco came out first.
Action 3:
Finish[San Marco]
Observation 3:
Episode finished
CoT
Question:
Was Vanderbilt University or Emory University founded first?
Thought:
Let’s think step by step.
Vanderbilt University was founded in 1873.
Emory
University was founded in 1836.
1873 (Vanderbilt University) > 1836 (Emory
University), so Vanderbilt University was founded first.
Answer:
Emory University
Failure: Reasoning error
ReAct
Question:
What was the middle name of the actress who was cast alongside Harvey
Fierstein, Linda Hart, Dick Latessa, Clarke Thorell, Mary Bond Davis, Laura
Bell Bundy, Matthew Morrison, Corey Reynolds, and Marissa Jaret Winokur in
Hairspray?
Thought 1:
I need to search Harvey Fierstein, Linda Hart, Dick Latessa, Clarke Thorell,
Mary Bond Davis, Laura Bell Bundy, Matthew Morrison, Corey Reynolds, and
Marissa Jaret Winokur, find the actress that was cast alongside them in
Hairspray, then find its middle name.
Action 1:
Search[Harvey Fierstein]
Observation 1:
Harvey Forbes Fierstein ...
Thought 2:
Harvey Fierstein is an actor, playwright, and screenwriter.
I need to
search Linda Hart next...
Action 2:
Search[Linda Hart]...
CoT
Question:
Who is older Danny Green or James Worthy?
Thought:
Let’s think step by step.
Danny Green was born in 1987.
James Worthy was
born in 1961.
1987 (Danny Green) > 1961 (James Worthy), so Danny Green is
older.
Answer:
Danny Green

###### 32


---
### 【第 33 页】


###### Published as a conference paper at ICLR 2023

Failure: Search error
ReAct
Question:
What does the goddess associated with the goddess frigg consists of what
tales?
Thought 1:
I need to search goddess frigg and find its associated goddess.
Action 1:
Search[goddess frigg]
Observation 1:
Could not find goddess frigg.
Similar:
[’Frigg’, ’Frigg and Freyja common
origin hypothesis’, ’Freyja (section Relation to Frigg and other goddesses
and figures)’, ’Eir (redirect from Eir (goddess))’, ’Baldr’].
Thought 2:
I need to search Frigg instead...
Failure: Hallucination
CoT
Question:
What was the first year a scientific journal published by an organization
located in the Bronx was published?
Thought:
Let’s think step by step.
The first year a scientific journal published by
an organization located in the Bronx was published was 1916.
Answer:
1916 (Label:
1909)
Failure: Label ambiguity
ReAct
Question:
What nationality is the man who developed the dictator game?
Thought 1:
I need to search dictator game, find the man who developed it, then find his
nationality.
Action 1:
Search[dictator game]
Observation 1:
The dictator game is a popular experimental instrument in social psychology
and economics...
Action 3:
Search[Amos Tversky]
Observation 3:
Amos Nathan Tversky...
Thought 4:
Amos Tversky is an Israeli cognitive and mathematical psychologist.
So the
man who developed the dictator game is Israeli.
Action 4:
Finish[Israeli] (label:
Israel-American)
CoT
Question:
Kurt Fuller from Stockton, CA appeared in which American Detective Comedy
Drama television series created by Steve Franks?
Thought:
Let’s think step by step.
Kurt Fuller from Stockton, CA appeared in Psych.
Psych is an American Detective Comedy Drama television series created by
Steve Franks.
Answer:
Psych (label:
Psych is an American detective comedy-drama)

###### 33


---

## 🔤 字体大小分布

| 字体大小 | 出现次数 | 角色 |
|----------|----------|------|
| 20.0 | 1 | heading_level_1 |
| 17.2 | 8 | heading_level_2 |
| 13.8 | 9 | heading_level_3 |
| 12.0 | 39 | heading_level_4 |
| 11.3 | 1 | heading_level_5 |
| 11.1 | 2 | heading_level_6 |
| 10.1 | 1401 | heading_level_7 |
| 10.0 | 902 | heading_level_8 |
| 9.9 | 321 | heading_level_9 |
| 9.8 | 1 | heading_level_10 |
| 9.6 | 28 | heading_level_11 |
| 9.1 | 1 | heading_level_12 |
| 9.0 | 12 | heading_level_13 |
| 8.8 | 64 | heading_level_14 |
| 8.5 | 19 | heading_level_15 |
| 8.3 | 33 | heading_level_16 |
| 8.0 | 58 | heading_level_17 |
| 7.0 | 7499 | body_text |
| 6.3 | 6 | minor |
| 6.2 | 1 | minor |
| 6.0 | 23 | minor |
| 5.8 | 21 | minor |
| 5.3 | 15 | minor |
| 5.2 | 14 | minor |
| 5.1 | 3 | minor |
| 5.0 | 98 | minor |
| 4.9 | 161 | minor |
| 4.6 | 29 | minor |
| 4.4 | 120 | minor |
| 4.2 | 10 | minor |
| 3.7 | 1 | minor |

---
*报告生成完毕*
