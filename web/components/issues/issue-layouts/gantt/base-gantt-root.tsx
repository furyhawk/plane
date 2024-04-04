import React, { useCallback } from "react";
import { observer } from "mobx-react-lite";
import { useRouter } from "next/router";
import useSWR from "swr";
import { TIssue,  } from "@plane/types";
//components
import { ChartDataType, GanttChartRoot, IBlockUpdateData, IssueGanttSidebar } from "@/components/gantt-chart";
import { getMonthChartItemPositionWidthInMonth } from "@/components/gantt-chart/views";
import { GanttQuickAddIssueForm, IssueGanttBlock } from "@/components/issues";
//constants
import { EIssueLayoutTypes, EIssuesStoreType } from "@/constants/issue";
import { EUserProjectRoles } from "@/constants/project";
import { getIssueBlocksStructure } from "@/helpers/issue.helper";
//hooks
import { useIssues, useUser } from "@/hooks/store";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
import { useIssuesActions } from "@/hooks/use-issues-actions";

import { ALL_ISSUES } from "@/store/issue/helpers/base-issues.store";
import { IssueLayoutHOC } from "../issue-layout-HOC";

type GanttStoreType =
  | EIssuesStoreType.PROJECT
  | EIssuesStoreType.MODULE
  | EIssuesStoreType.CYCLE
  | EIssuesStoreType.PROJECT_VIEW;

export const BaseGanttRoot: React.FC = observer(() => {
  // router
  const router = useRouter();
  const { workspaceSlug } = router.query;

  const storeType = useIssueStoreType() as GanttStoreType;
  const { issues, issuesFilter, issueMap } = useIssues(storeType);
  const { fetchIssues, fetchNextIssues, updateIssue, quickAddIssue } = useIssuesActions(storeType);
  // store hooks
  const {
    membership: { currentProjectRole },
  } = useUser();
  const appliedDisplayFilters = issuesFilter.issueFilters?.displayFilters;

  useSWR(`ISSUE_GANTT_LAYOUT_${storeType}`, () => fetchIssues("init-loader", { canGroup: false, perPageCount: 100 }), {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  });

  const issuesIds = (issues.groupedIssueIds?.[ALL_ISSUES] as string[]) ?? [];
  const nextPageResults = issues.getPaginationData(undefined, undefined)?.nextPageResults;

  const { enableIssueCreation } = issues?.viewFlags || {};

  const loadMoreIssues = useCallback(() => {
    fetchNextIssues();
  }, [fetchNextIssues]);

  const getBlockById = useCallback(
    (id: string, currentViewData?: ChartDataType | undefined) => {
      const issue = issueMap[id];
      const block = getIssueBlocksStructure(issue);
      if (currentViewData) {
        return {
          ...block,
          position: getMonthChartItemPositionWidthInMonth(currentViewData, block),
        };
      }
      return block;
    },
    [issueMap]
  );

  const updateIssueBlockStructure = async (issue: TIssue, data: IBlockUpdateData) => {
    if (!workspaceSlug) return;

    const payload: any = { ...data };
    if (data.sort_order) payload.sort_order = data.sort_order.newSortOrder;

    updateIssue && (await updateIssue(issue.project_id, issue.id, payload));
  };

  const isAllowed = !!currentProjectRole && currentProjectRole >= EUserProjectRoles.MEMBER;

  return (
    <IssueLayoutHOC layout={EIssueLayoutTypes.GANTT}>
      <div className="h-full w-full">
        <GanttChartRoot
          border={false}
          title="Issues"
          loaderTitle="Issues"
          blockIds={issuesIds}
          getBlockById={getBlockById}
          blockUpdateHandler={updateIssueBlockStructure}
          blockToRender={(data: TIssue) => <IssueGanttBlock issueId={data.id} />}
          sidebarToRender={(props) => <IssueGanttSidebar {...props} showAllBlocks />}
          enableBlockLeftResize={isAllowed}
          enableBlockRightResize={isAllowed}
          enableBlockMove={isAllowed}
          enableReorder={appliedDisplayFilters?.order_by === "sort_order" && isAllowed}
          enableAddBlock={isAllowed}
          quickAdd={
            enableIssueCreation && isAllowed ? <GanttQuickAddIssueForm quickAddCallback={quickAddIssue} /> : undefined
          }
          loadMoreBlocks={loadMoreIssues}
          canLoadMoreBlocks={nextPageResults}
          showAllBlocks
        />
      </div>
    </IssueLayoutHOC>
  );
});
