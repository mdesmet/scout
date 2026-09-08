import { test, expect } from "@playwright/test";

test("empty workspace and explicit synthetic walkthrough",async({page})=>{
 const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
 await page.goto("/");
 await expect(page.getByRole("heading",{name:/Find a problem/})).toBeVisible();
 await expect(page.getByRole("button",{name:"Start scouting"})).toBeDisabled();
 await page.getByRole("button",{name:"Explore an example"}).click();
 await expect(page).toHaveURL(/\/opportunities\/example$/);
 await expect(page.getByText(/Synthetic example. All people/)).toBeVisible();
 await page.getByRole("button",{name:/A release check for AI-generated metrics/}).click();
 await expect(page).toHaveURL(/\/opportunities\/example\/O1$/);
 await expect(page.getByRole("heading",{name:"Competitor and substitute landscape"})).toBeVisible();
 await expect(page.getByRole("heading",{name:"User and buyer"})).toBeVisible();
 await expect(page.getByText("Analytics engineer responsible for recurring customer reports")).toBeVisible();
 await expect(page.getByText("Analytics engineering lead accountable for report reliability")).toBeVisible();
 await page.getByRole("button",{name:"Scorecard",exact:true}).click();
 await expect(page.locator(".score-card")).toHaveCount(9);
 await expect(page.getByRole("button",{name:"Record outcome"})).toBeDisabled();
 await page.getByRole("button",{name:"Pain & evidence"}).click();
 await expect(page.getByRole("heading",{name:"Evidence ledger"})).toBeVisible();
 await page.screenshot({path:"test-results/scorecard-evidence.png",fullPage:true});
 expect(errors).toEqual([]);
 await page.reload();
 await expect(page.getByRole("heading",{name:/A release check for AI-generated metrics/})).toBeVisible();
 await page.goBack();
 await expect(page.getByRole("heading",{name:"The opportunity landscape."})).toBeVisible();
});

test("memory editing, disabling, forgetting, and undo",async({page})=>{
 await page.goto("/");
 await page.getByRole("button",{name:"Memory",exact:true}).click();
 await expect(page).toHaveURL(/\/memory$/);
 await page.getByRole("button",{name:"Add preference"}).click();
 await page.getByLabel("What should Scout remember?").fill("Prefer tools with self-serve adoption.");
 await page.getByRole("button",{name:"Save preference"}).click();
 const card=page.locator(".memory-card").filter({hasText:"Prefer tools with self-serve adoption."});
 await expect(card).toBeVisible();
 await card.getByTitle("Disable preference").click();
 await expect(card.getByText("Disabled",{exact:true})).toBeVisible();
 await card.getByTitle("Undo last memory change").click();
 await expect(card.getByText("Disabled",{exact:true})).toHaveCount(0);
 await card.getByTitle("Forget preference").click();
 await expect(page.getByText("Removed from future research context.")).toBeVisible();
});

test("discover founder-matched prompts and start from one",async({page})=>{
 await page.goto("/directions");
 await expect(page.getByRole("heading",{name:"Discover your next search direction."})).toBeVisible();
 await page.getByRole("button",{name:"Discover directions"}).click();
 await expect(page.getByRole("heading",{name:"Release assurance for AI analytics"})).toBeVisible();
 await expect(page.getByRole("heading",{name:"Directions worth investigating"})).toBeVisible();
 await expect(page.getByText("Analytics engineer",{exact:true})).toBeVisible();
 await expect(page.getByText("Synthetic problem signal",{exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Use as scout brief"}).click();
 await expect(page).toHaveURL(/\/scout$/);
 await expect(page.getByLabel("What do you want to explore?")).toHaveValue("AI analytics release assurance");
 await expect(page.getByLabel("What else should Scout know?")).toHaveValue(/Verify recurring release-review pain/);
});

test("research can be paused, redirected, completed, and calibrated",async({page})=>{
 await page.goto("/");
 await page.getByLabel("What do you want to explore?").fill("AI data integration");
 await page.getByRole("button",{name:"Start scouting"}).click();
 await expect(page.getByRole("button",{name:"Pause",exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Pause",exact:true}).click();
 await expect(page.getByRole("button",{name:"Resume research"})).toBeVisible();
 await page.getByLabel("Steer the search",{exact:true}).fill("Prefer narrow developer tools with low support.");
 await page.getByLabel("Steering impact").selectOption("product_reframing");
 await page.getByLabel("Remember for future searches").check();
 await page.getByRole("button",{name:"Apply direction"}).click();
 await expect(page.getByText(/CURRENT SCOUT · BRIEF V2/)).toBeVisible();
 await expect(page.getByText(/Product reframing · resumes at/)).toBeVisible();
 await expect(page.getByRole("button",{name:"View scorecards"})).toBeVisible({timeout:20000});
 await page.getByRole("button",{name:"View scorecards"}).click();
 await page.getByRole("button",{name:/A release check for AI-generated metrics/}).click();
 await page.getByRole("button",{name:"Record outcome"}).click();
 await page.getByLabel("What happened?",{exact:true}).fill("One customer agreed to a paid pilot. Amount is USD.");
 await page.getByLabel("Outcome",{exact:true}).selectOption("paid");
 await page.getByLabel("Amount, if applicable").fill("250");
 await page.getByRole("button",{name:"Save feedback"}).click();
 await page.getByRole("button",{name:"Reports",exact:true}).click();
 await expect(page.getByText("Worth validating → paid")).toBeVisible();
 const response=await page.request.get("/api/runs");
 const runs=await response.json();const live=runs.find((r:any)=>!r.demo);
 const csv=await page.request.get("/api/runs/"+live.id+"/export/csv");
 expect(csv.ok()).toBeTruthy();
 expect(await csv.text()).toContain("pain_severity");
});

test("mobile workspace fits and supports founder context",async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto("/");
 await expect(page.getByRole("heading",{name:/Find a problem/})).toBeVisible();
 const width=await page.evaluate(()=>document.documentElement.scrollWidth);
 expect(width).toBeLessThanOrEqual(390);
 await page.screenshot({path:"test-results/mobile-scout.png",fullPage:true});
 await page.getByRole("button",{name:"Memory",exact:true}).click();
 await expect(page.getByRole("heading",{name:"What Scout is learning."})).toBeVisible();
});

test("investigate an unknown and compare a linked report without changing the parent",async({page})=>{
 const created=await page.request.post("/api/runs",{data:{keywords:"Followup unknown demo"}});
 expect(created.ok()).toBeTruthy();
 const parent=await created.json();
 await expect.poll(async()=>{const r=await page.request.get("/api/runs/"+parent.id);return(await r.json()).status;}).toBe("completed");
 const baseline=await(await page.request.get("/api/runs/"+parent.id)).json();
 await page.goto("/");
 await page.getByRole("button",{name:"Opportunities",exact:true}).click();
 await page.getByRole("combobox",{name:"Select research run"}).selectOption(parent.id);
 await page.getByRole("button",{name:/A release check for AI-generated metrics/}).click();
 await page.getByRole("button",{name:"Scorecard",exact:true}).click();
 const card=page.locator(".score-card").filter({has:page.getByRole("heading",{name:"Willingness to pay",exact:true})});
 await expect(card.getByText("Unknown",{exact:true})).toBeVisible();
 await card.getByRole("button",{name:"Investigate Willingness to pay",exact:true}).click();
 await expect(page.getByRole("dialog",{name:"Investigate Willingness to pay"})).toBeVisible();
 await page.getByLabel("What should this follow-up investigate?").fill("Find customers paying for the exact current workaround.");
 await page.getByRole("button",{name:"Start focused research"}).click();
 await expect(page.locator(".steps>div")).toHaveCount(3);
 await expect(page.getByRole("button",{name:"View scorecards"})).toBeVisible({timeout:20000});
 await page.getByRole("button",{name:"View scorecards"}).click();
 const summary=page.locator(".investigation-summary");
 await expect(summary).toContainText("Unknown");
 await expect(summary).toContainText("4/5");
 await expect(summary).toContainText("A synthetic buyer reports paying for a workaround.");
 await expect(summary).toContainText("The other eight scores are preserved.");
 const allRuns=await(await page.request.get("/api/runs")).json();
 const child=allRuns.find((r:any)=>r.parent_run_id===parent.id);
 const current=await(await page.request.get("/api/runs/"+child.id)).json();
 expect(current.report.investigation.new_source_ids).toEqual(["N1"]);
 const parentAfter=await(await page.request.get("/api/runs/"+parent.id)).json();
 expect(parentAfter.report).toEqual(baseline.report);
 const other=(r:any)=>r.report.opportunities[0].scores.filter((s:any)=>s.dimension!=="willingness_to_pay");
 expect(other(current)).toEqual(other(baseline));
 await page.screenshot({path:"test-results/investigation-comparison.png",fullPage:true});
 await page.getByRole("button",{name:"Original report",exact:true}).click();
 await expect(page.getByRole("combobox",{name:"Select research run"})).toHaveValue(parent.id);
});

test("reframe an old direction into a product and market report",async({page})=>{
 const runs=await(await page.request.get("/api/runs")).json();
 const parent=runs.find((r:any)=>!r.demo&&!r.parent_run_id&&!r.reframed_from_run_id&&r.status==="completed");
 const before=await(await page.request.get("/api/runs/"+parent.id)).json();
 await page.goto("/");
 await page.getByRole("button",{name:"Opportunities",exact:true}).click();
 await page.getByRole("combobox",{name:"Select research run"}).selectOption(parent.id);
 await page.getByRole("button",{name:/A release check for AI-generated metrics/}).click();
 await page.getByRole("button",{name:"Reframe as a product"}).click();
 await page.getByLabel("What should the product research focus on?").fill("Connect the recurring workflow pains and compare paid competitors.");
 await page.getByRole("button",{name:"Research product & market",exact:true}).click();
 await expect(page.locator(".steps>div")).toHaveCount(7);
 await expect(page.getByRole("button",{name:"View scorecards"})).toBeVisible({timeout:20000});
 await page.getByRole("button",{name:"View scorecards"}).click();
 await page.getByRole("button",{name:/A release check for AI-generated metrics/}).click();
 await expect(page.getByRole("heading",{name:"Competitor and substitute landscape"})).toBeVisible();
 await expect(page.getByRole("heading",{name:"The market case",exact:true})).toBeVisible();
 await expect(page.getByText("2 related pains",{exact:true})).toBeVisible();
 await page.screenshot({path:"test-results/product-market.png",fullPage:true});
 const after=await(await page.request.get("/api/runs/"+parent.id)).json();
 expect(after.report).toEqual(before.report);
});

test("feature-sized findings are not presented as product cases",async({page})=>{
 const created=await page.request.post("/api/runs",{data:{keywords:"Feature-only test"}});
 const run=await created.json();
 await expect.poll(async()=>{const r=await page.request.get("/api/runs/"+run.id);return(await r.json()).status;}).toBe("completed");
 await page.goto("/");
 await page.getByRole("button",{name:"Opportunities",exact:true}).click();
 await page.getByRole("combobox",{name:"Select research run"}).selectOption(run.id);
 await expect(page.locator(".report-summary")).toBeVisible();
 await expect(page.locator(".opportunity-card")).toHaveCount(0);
 await page.getByRole("button",{name:/Rejected/}).click();
 await expect(page.locator(".opportunity-card")).toHaveCount(1);
});

test("early-stop report explains findings and rejection trail",async({page})=>{
 const created=await page.request.post("/api/runs",{data:{keywords:"Empty synthesis trail test"}});const run=await created.json();
 await expect.poll(async()=>{const r=await page.request.get("/api/runs/"+run.id);return(await r.json()).status;}).toBe("completed");
 await page.goto("/");await page.getByRole("button",{name:"Opportunities",exact:true}).click();
 await page.getByRole("combobox",{name:"Select research run"}).selectOption(run.id);
 const trail=page.locator(".decision-trail");
 await expect(trail.getByRole("heading",{name:"See how Scout reached this result"})).toBeVisible();
 await expect(trail.getByRole("heading",{name:"No coherent product thesis"})).toBeHidden();
 await trail.locator(":scope > summary").click();
 await expect(trail.getByLabel("Research phases")).toBeVisible();
 await trail.locator('.trail-phase[data-stage="product_synthesis"] > summary').click();
 await expect(trail.getByRole("heading",{name:"No coherent product thesis"})).toBeVisible();
 await expect(trail.getByText("Rejected",{exact:true})).toBeVisible();
 await trail.getByText("What could advance or reopen this?").last().click();
 await expect(trail.getByText(/Find multiple related pains/)).toBeVisible();
 await expect(page.locator(".opportunity-card")).toHaveCount(0);
});

test("research trail is optional and explains relationships by phase",async({page})=>{
 const created=await page.request.post("/api/runs",{data:{keywords:"Trail relationship test"}});const run=await created.json();
 await expect.poll(async()=>{const r=await page.request.get("/api/runs/"+run.id);return(await r.json()).status;}).toBe("completed");
 await page.goto("/opportunities/"+run.id);
 const trail=page.locator(".decision-trail");
 await expect(trail).not.toHaveAttribute("open","");
 await expect(trail.locator(".trail-body")).toBeHidden();
 await trail.locator(":scope > summary").click();
 await expect(trail.getByLabel("Research phases")).toBeVisible();
});
